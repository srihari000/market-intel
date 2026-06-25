import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.analyzer import analyze

MOCK_JSON = json.dumps({
    "themes": [{"theme": "AI growth", "summary": "AI is expanding rapidly.", "source_indices": [0]}],
    "competitor_activities": [{"competitor": "OpenAI", "activity": "Launched new model", "source_index": 0}],
})


@pytest.mark.asyncio
async def test_analyze_returns_structured_report():
    mock_choice = MagicMock()
    mock_choice.message.content = MOCK_JSON
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("app.services.analyzer.AsyncAzureOpenAI", return_value=mock_client):
        result = await analyze(
            sources={"https://example.com": "OpenAI launched a new model for AI growth."},
            competitors=["OpenAI"],
            topics=["AI"],
        )

    assert "themes" in result
    assert "competitor_activities" in result
    assert result["themes"][0]["theme"] == "AI growth"
    assert result["competitor_activities"][0]["competitor"] == "OpenAI"
