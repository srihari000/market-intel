import json
import logging
# --- OpenAI Direct (active) ---
from openai import AsyncOpenAI
# --- Azure OpenAI (uncomment to switch from direct OpenAI to Azure OpenAI) ---
# from openai import AsyncAzureOpenAI
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from pydantic import ValidationError

from app.config import settings
from app.schemas.llm import AnalysisOutput
from app.utils.retry import llm_retry
from app.utils.llm_guard import sanitize_user_input, sanitize_scraped_content, truncate_to_token_budget, count_tokens

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior market research analyst. Given scraped web content, a list of competitors to track, and topics of interest, extract a structured market intelligence report.

Return ONLY valid JSON with this exact structure:
{
  "themes": [
    {"theme": "theme name", "summary": "2-3 sentence summary", "source_indices": [0, 1]}
  ],
  "competitor_activities": [
    {"competitor": "Company Name", "activity": "what they did", "source_index": 0}
  ]
}

Rules for themes:
- Extract ALL key themes and developments from the sources that relate to the given topics area
- Topics are a general domain guide (e.g. "AI Coding" means anything about AI, coding tools, developer products, LLMs for code, etc.)
- Do not require exact topic phrase matches — interpret topics broadly
- A theme can be about any company or trend found in the sources, as long as it is relevant to the topic area

Rules for competitor_activities:
- Only include entries for competitors that are explicitly named in the sources
- If a listed competitor does not appear in the sources, skip them — do not fabricate
- Record what they launched, announced, changed, or are known for based on the source content

General rules:
- source_indices and source_index are 0-based indexes into the sources array provided
- Only include information explicitly present in the sources — do not invent facts
- If the content is genuinely irrelevant to the topic area, return empty arrays
"""


def _build_sources_text(sources: dict[str, str]) -> str:
    """Sanitize + truncate sources to fit token budget accurately."""
    # Sanitize each source for injection patterns before building prompt
    sanitized = {url: sanitize_scraped_content(text) for url, text in sources.items()}
    # Token-accurate truncation — reserve 4k tokens for system prompt + response
    truncated = truncate_to_token_budget(sanitized, budget=124_000)
    return "\n\n".join(
        f"SOURCE {i} ({url}):\n{text}"
        for i, (url, text) in enumerate(truncated.items())
    )


@llm_retry(max_attempts=3, base_delay=1.0)
async def _call_llm(client: AsyncOpenAI, user_message: str) -> str:
    response = await client.chat.completions.create(
        model=settings.OPENAI_ANALYZER_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        timeout=60,
    )
    return response.choices[0].message.content


@traceable(name="market_analyzer", run_type="chain")
async def analyze(sources: dict[str, str], competitors: list[str], topics: list[str]) -> dict:
    logger.info(
        "Analyzer start — sources: %d, competitors: %s, topics: %s",
        len(sources), competitors or "any", topics or "any",
    )

    # --- OpenAI Direct (active) ---
    client = wrap_openai(AsyncOpenAI(api_key=settings.OPENAI_API_KEY))
    # --- Azure OpenAI (uncomment to switch from direct OpenAI to Azure OpenAI) ---
    # client = AsyncAzureOpenAI(
    #     api_key=settings.AZURE_OPENAI_API_KEY,
    #     azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    #     api_version=settings.AZURE_OPENAI_API_VERSION,
    # )

    # Sanitize user-supplied inputs before inserting into prompt
    safe_competitors = [sanitize_user_input(c) for c in competitors]
    safe_topics = [sanitize_user_input(t) for t in topics]

    sources_text = _build_sources_text(sources)
    user_message = (
        f"Competitors to track: {', '.join(safe_competitors) or 'any'}\n"
        f"Topics to focus on: {', '.join(safe_topics) or 'any'}\n\n"
        f"SOURCES:\n{sources_text}\n\n"
        "Return the market intelligence report as JSON."
    )
    logger.debug("Prompt tokens: %d", count_tokens(user_message))

    logger.debug(
        "Sending %d chars to OpenAI (%s)", len(user_message), settings.OPENAI_ANALYZER_MODEL
    )

    raw = await _call_llm(client, user_message)

    # Validate and coerce LLM output — never trust raw JSON from an LLM
    try:
        parsed = json.loads(raw)
        validated = AnalysisOutput.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error("LLM returned invalid analysis structure: %s | raw: %.200s", exc, raw)
        raise ValueError(f"Analyzer returned malformed response: {exc}") from exc

    result = validated.model_dump()
    logger.info(
        "Analyzer done — themes: %d, competitor_activities: %d",
        len(result["themes"]),
        len(result["competitor_activities"]),
    )
    return result
