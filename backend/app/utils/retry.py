import asyncio
import logging
import random
from functools import wraps
from typing import Callable, TypeVar

import openai

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Errors worth retrying — transient infrastructure issues
_RETRYABLE = (
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.InternalServerError,
)

# Errors that should never be retried — caller mistake or bad config
_TERMINAL = (
    openai.AuthenticationError,
    openai.PermissionDeniedError,
    openai.NotFoundError,
    openai.UnprocessableEntityError,
)


def llm_retry(max_attempts: int = 3, base_delay: float = 1.0):
    """Exponential backoff with jitter for transient LLM errors."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except _TERMINAL as exc:
                    # Never retry — wrong key, bad request, etc.
                    logger.error("Terminal LLM error (will not retry): %s", exc)
                    raise
                except _RETRYABLE as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "LLM call failed after %d attempts: %s", max_attempts, exc
                        )
                        raise
                    # Full jitter: random(0, base * 2^attempt) — avoids thundering herd
                    ceiling = base_delay * (2 ** attempt)
                    delay = random.uniform(0, ceiling)
                    logger.warning(
                        "Transient LLM error (attempt %d/%d), retrying in %.1fs: %s",
                        attempt, max_attempts, delay, type(exc).__name__,
                    )
                    await asyncio.sleep(delay)
                except Exception as exc:
                    # Unknown error — retry once, then re-raise
                    if attempt == max_attempts:
                        raise
                    logger.warning(
                        "Unexpected LLM error (attempt %d/%d): %s", attempt, max_attempts, exc
                    )
                    await asyncio.sleep(base_delay)
        return wrapper
    return decorator
