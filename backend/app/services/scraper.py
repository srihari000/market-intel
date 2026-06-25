from typing import Optional
import httpx
from bs4 import BeautifulSoup

SCRAPE_TIMEOUT = 15.0
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MarketIntelBot/1.0)"}
MAX_CHARS = 50_000


async def scrape_url(url: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=SCRAPE_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())[:MAX_CHARS]
    except Exception:
        return None
