import json
import logging
# --- OpenAI Direct (active) ---
from openai import AsyncOpenAI
# --- Azure OpenAI (commented out — switch back when Azure access is approved) ---
# from openai import AsyncAzureOpenAI
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from pydantic import ValidationError

from app.config import settings
from app.schemas.llm import JudgeOutput
from app.utils.retry import llm_retry
from app.utils.llm_guard import sanitize_scraped_content, count_tokens

logger = logging.getLogger(__name__)

# Judge only needs enough context to verify claims — cap per source
MAX_SOURCE_CHARS_FOR_JUDGE = 10_000

JUDGE_PROMPT = """You are a skeptical fact-checker. You receive a market intelligence report and the original source text it was derived from.

Verify every theme and competitor activity claim against the sources.

For each theme (in order), return a verdict in theme_verdicts.
For each competitor activity (in order), return a verdict in activity_verdicts.

Each verdict must have:
- status: "verified" if the claim is clearly supported by the source, "flagged" if not
- confidence: float 0.0-1.0 (how confident you are in the claim being supported)
- reason: empty string if verified, brief explanation if flagged

Return ONLY valid JSON:
{
  "theme_verdicts": [
    {"status": "verified", "confidence": 0.95, "reason": ""},
    {"status": "flagged", "confidence": 0.40, "reason": "Not explicitly stated in source"}
  ],
  "activity_verdicts": [
    {"status": "verified", "confidence": 0.90, "reason": ""}
  ],
  "overall_score": 0.92,
  "reasoning": "Brief overall assessment of report accuracy"
}

Rules:
- theme_verdicts must have exactly the same number of entries as themes (in same order)
- activity_verdicts must have exactly the same number of entries as competitor_activities (in same order)
- overall_score = (verified_count) / (total_claims) as float 0.0-1.0
- If report is empty, return empty arrays and overall_score 1.0
"""


@llm_retry(max_attempts=3, base_delay=1.0)
async def _call_llm(client: AsyncOpenAI, user_message: str) -> str:
    response = await client.chat.completions.create(
        model=settings.OPENAI_JUDGE_MODEL,
        messages=[
            {"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
        timeout=60,
    )
    return response.choices[0].message.content


@traceable(name="hallucination_judge", run_type="chain")
async def judge(report: dict, sources: dict[str, str]) -> dict:
    themes = report.get("themes", [])
    activities = report.get("competitor_activities", [])
    logger.info(
        "Judge start — verifying %d themes and %d competitor activities",
        len(themes), len(activities),
    )

    # If the report is empty, skip LLM call entirely
    if not themes and not activities:
        logger.info("Judge short-circuit — empty report, score 1.0")
        return {"theme_verdicts": [], "activity_verdicts": [], "overall_score": 1.0, "reasoning": "No claims to verify."}

    # --- OpenAI Direct (active) ---
    client = wrap_openai(AsyncOpenAI(api_key=settings.OPENAI_API_KEY))
    # --- Azure OpenAI (commented out — switch back when Azure access is approved) ---
    # client = AsyncAzureOpenAI(
    #     api_key=settings.AZURE_OPENAI_API_KEY,
    #     azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    #     api_version=settings.AZURE_OPENAI_API_VERSION,
    # )

    sources_text = "\n\n".join(
        f"SOURCE {i} ({url}):\n{sanitize_scraped_content(text[:MAX_SOURCE_CHARS_FOR_JUDGE])}"
        for i, (url, text) in enumerate(sources.items())
    )

    user_message = (
        f"REPORT TO VERIFY:\n{json.dumps(report, indent=2)}\n\n"
        f"ORIGINAL SOURCES:\n{sources_text}\n\n"
        "Return the hallucination verdict as JSON."
    )
    logger.debug("Judge prompt tokens: %d", count_tokens(user_message))

    raw = await _call_llm(client, user_message)

    # Validate and coerce — score is clamped to [0, 1] by the schema validator
    try:
        parsed = json.loads(raw)
        validated = JudgeOutput.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error("LLM returned invalid judge structure: %s | raw: %.200s", exc, raw)
        # Safe fallback: treat as low confidence so pipeline can retry
        return {"theme_verdicts": [], "activity_verdicts": [], "overall_score": 0.0, "reasoning": f"Judge parse error: {exc}"}

    result = validated.model_dump()
    score = result["overall_score"]
    flagged = sum(1 for v in result["theme_verdicts"] + result["activity_verdicts"] if v["status"] == "flagged")
    logger.info("Judge done — overall_score: %.2f, flagged: %d", score, flagged)
    return result
