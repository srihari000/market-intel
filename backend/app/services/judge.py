import json
from openai import AsyncAzureOpenAI
from app.config import settings

JUDGE_PROMPT = """You are a skeptical fact-checker. You receive a market intelligence report and the original source text it was derived from. Verify every claim.

Flag any claim that:
- Is not explicitly found in the sources
- Overstates what a source says
- Combines information from sources in a misleading way

Return ONLY valid JSON with this exact structure:
{
  "score": 0.95,
  "flagged_claims": [
    {"claim": "exact claim from report", "reason": "why it is unsupported"}
  ],
  "reasoning": "brief overall assessment"
}

score = (total_claims - flagged) / total_claims as a float 0.0-1.0.
If all claims are verified, score is 1.0 and flagged_claims is [].
"""


async def judge(report: dict, sources: dict[str, str]) -> dict:
    client = AsyncAzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )

    sources_text = "\n\n".join(
        f"SOURCE {i} ({url}):\n{text[:10_000]}"
        for i, (url, text) in enumerate(sources.items())
    )

    user_message = f"""REPORT TO VERIFY:
{json.dumps(report, indent=2)}

ORIGINAL SOURCES:
{sources_text}

Return the hallucination verdict as JSON."""

    response = await client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )

    return json.loads(response.choices[0].message.content)
