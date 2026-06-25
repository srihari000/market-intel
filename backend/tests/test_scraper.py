import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.scraper import scrape_url


@pytest.mark.asyncio
async def test_scrape_url_returns_clean_text():
    mock_response = MagicMock()
    mock_response.text = "<html><body><nav>Skip</nav><p>Hello world content</p><script>js</script></body></html>"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.services.scraper.httpx.AsyncClient", return_value=mock_client):
        result = await scrape_url("https://example.com")

    assert result is not None
    assert "Hello world content" in result
    assert "<nav>" not in result


@pytest.mark.asyncio
async def test_scrape_url_returns_none_on_error():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=Exception("Connection error"))

    with patch("app.services.scraper.httpx.AsyncClient", return_value=mock_client):
        result = await scrape_url("https://bad-url.invalid")

    assert result is None
