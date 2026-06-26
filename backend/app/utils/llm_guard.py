"""
LLM security utilities — prompt injection defense and token management.
"""
import logging
import re
import tiktoken

logger = logging.getLogger(__name__)

# GPT-4o context: 128k tokens. Reserve 4k for system prompt + response.
MAX_PROMPT_TOKENS = 124_000

# Patterns that indicate prompt injection attempts in user-supplied text
_INJECTION_PATTERNS = re.compile(
    r"(ignore (all |previous |above |prior )?instructions?|"
    r"disregard (all |previous )?instructions?|"
    r"system\s*:|assistant\s*:|human\s*:|<\|im_start\|>|<\|im_end\|>|"
    r"you are now|new instructions?|override instructions?|"
    r"forget (all |your |previous )?instructions?|"
    r"do not follow|stop being|act as if|pretend (you are|to be)|"
    r"reveal (your |the )?system prompt|"
    r"print (your |the )?system prompt|"
    r"what (are|were) your instructions)",
    re.IGNORECASE,
)

_encoder = None


def _get_encoder() -> tiktoken.Encoding:
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")  # GPT-4o uses cl100k_base
    return _encoder


def count_tokens(text: str) -> int:
    return len(_get_encoder().encode(text))


def sanitize_user_input(value: str) -> str:
    """
    Strip prompt injection attempts from user-supplied strings
    (competitors, topics, title).
    """
    if _INJECTION_PATTERNS.search(value):
        logger.warning("Prompt injection attempt detected in user input: %.80s", value)
        # Replace the entire matched phrase — don't try to partially clean it
        cleaned = _INJECTION_PATTERNS.sub("[removed]", value)
        return cleaned.strip()
    return value


def sanitize_scraped_content(text: str) -> str:
    """
    Sanitize scraped web content before inserting into LLM prompt.
    Removes role-prefix tokens and injection phrases that could hijack
    the model's instruction-following behavior.
    """
    # Strip role prefixes that some models treat as special tokens
    text = re.sub(r"(?m)^(system|assistant|human|user)\s*:\s*", "", text, flags=re.IGNORECASE)

    # Remove OpenAI special tokens
    text = re.sub(r"<\|im_(start|end)\|>", "", text)

    if _INJECTION_PATTERNS.search(text):
        logger.warning("Prompt injection pattern found in scraped content — sanitizing")
        text = _INJECTION_PATTERNS.sub("[content removed]", text)

    return text


def truncate_to_token_budget(sources: dict[str, str], budget: int = MAX_PROMPT_TOKENS) -> dict[str, str]:
    """
    Truncate source texts so total token count stays within budget.
    Uses actual tiktoken counts — not char estimation.
    """
    encoder = _get_encoder()
    result: dict[str, str] = {}
    remaining = budget

    for url, text in sources.items():
        tokens = encoder.encode(text)
        if len(tokens) <= remaining:
            result[url] = text
            remaining -= len(tokens)
        elif remaining > 100:
            # Partial include — decode only what fits
            truncated = encoder.decode(tokens[:remaining])
            result[url] = truncated
            logger.warning(
                "Source truncated from %d to %d tokens to fit budget: %s",
                len(tokens), remaining, url,
            )
            remaining = 0
            break
        else:
            logger.warning("Source dropped — no token budget left: %s", url)
            break

    return result
