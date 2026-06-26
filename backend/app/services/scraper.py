import asyncio
import ipaddress
import logging
import socket
from typing import Optional
from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SCRAPE_TIMEOUT = 15.0
MAX_CHARS = 50_000
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_REDIRECTS = 5
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MarketIntelBot/1.0)"}

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / AWS metadata
    ipaddress.ip_network("100.64.0.0/10"),   # carrier-grade NAT
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


async def _resolve_ip(hostname: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, socket.gethostbyname, hostname)


async def _is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname or ""
    if not hostname or hostname in ("localhost", "0.0.0.0", "metadata.google.internal"):
        return False
    try:
        resolved = await _resolve_ip(hostname)
        ip = ipaddress.ip_address(resolved)
        if any(ip in net for net in _PRIVATE_NETWORKS):
            logger.warning("SSRF blocked — %s resolved to private IP %s", hostname, resolved)
            return False
    except Exception as exc:
        logger.warning("DNS resolution failed for %s: %s", hostname, exc)
        return False
    return True


async def scrape_url(url: str) -> Optional[str]:
    logger.info("Scraping URL: %s", url)

    if not await _is_safe_url(url):
        logger.warning("Blocked unsafe URL: %s", url)
        return None

    try:
        # follow_redirects=False — each hop is checked for SSRF before following
        async with httpx.AsyncClient(
            timeout=SCRAPE_TIMEOUT,
            follow_redirects=False,
            headers=HEADERS,
        ) as client:
            current_url = url
            for hop in range(MAX_REDIRECTS):
                response = await client.get(current_url)
                if response.is_redirect:
                    location = response.headers.get("location", "")
                    if not await _is_safe_url(location):
                        logger.warning("Redirect to unsafe URL blocked: %s", location)
                        return None
                    logger.debug("Redirect %d: %s → %s", hop + 1, current_url, location)
                    current_url = location
                    continue
                break
            else:
                logger.warning("Too many redirects for %s", url)
                return None

            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if not any(t in content_type for t in ("text/html", "text/plain", "application/xhtml")):
                logger.warning("Skipping non-HTML content-type '%s' from %s", content_type, url)
                return None

            if len(response.content) > MAX_RESPONSE_BYTES:
                logger.warning("Response too large (%d bytes) from %s", len(response.content), url)
                return None

        # Trafilatura extracts main article content, removes ads/nav/boilerplate
        text = trafilatura.extract(
            response.text,
            include_comments=False,
            include_tables=True,
            no_fallback=False,      # fall back to BeautifulSoup if trafilatura finds nothing
            favor_precision=False,  # favor recall — get more content
        )

        # Fallback to BeautifulSoup if trafilatura returns nothing
        # (happens on pages with no clear main content block)
        if not text:
            logger.debug("Trafilatura found no content for %s — falling back to BeautifulSoup", url)
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = " ".join(soup.get_text(separator=" ", strip=True).split())

        text = (text or "")[:MAX_CHARS]
        logger.info("Scraped %s — %d chars extracted", url, len(text))
        return text or None

    except httpx.HTTPStatusError as exc:
        logger.warning("HTTP %s scraping %s", exc.response.status_code, url)
        return None
    except httpx.TimeoutException:
        logger.warning("Timeout scraping %s (limit %ss)", url, SCRAPE_TIMEOUT)
        return None
    except Exception as exc:
        logger.warning("Failed to scrape %s: %s", url, exc)
        return None
