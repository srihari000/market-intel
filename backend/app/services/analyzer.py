import json
from openai import AsyncAzureOpenAI
from app.config import settings

SYSTEM_PROMPT = """You are a senior market research analyst. Given scraped web content and a list of competitors and topics, extract a structured market intelligence report.

Return ONLY valid JSON with this exact structure:
{
  "themes": [
    {"theme": "theme name", "summary": "2-3 sentence summary", "source_indices": [0, 1]}
  ],
  "competitor_activities": [
    {"competitor": "Company Name", "activity": "what they did", "source_index": 0}
  ]
}

Rules:
- source_indices and source_index are 0-based indexes into the sources array provided
- Only include information explicitly present in the sources
- Do not invent or infer any facts
"""


async def analyze(sources: dict[str, str], competitors: list[str], topics: list[str]) -> dict:
    client = AsyncAzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )

    sources_text = "\n\n".join(
        f"SOURCE {i} ({url}):\n{text}"
        for i, (url, text) in enumerate(sources.items())
    )

    user_message = f"""Competitors to track: {', '.join(competitors) or 'any'}
Topics to focus on: {', '.join(topics) or 'any'}

SOURCES:
{sources_text}

Return the market intelligence report as JSON."""

    response = await client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    return json.loads(response.choices[0].message.content)
