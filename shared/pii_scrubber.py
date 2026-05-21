"""
PII scrubber — strips personally identifiable information from review text
before it is stored or sent to an LLM.

Patterns removed / replaced:
  - Email addresses          → [EMAIL]
  - Phone numbers (IN + intl) → [PHONE]
  - URLs / links             → [URL]
  - @mentions                → [USER]
  - Aadhaar-style 12-digit numbers → [ID]
"""
import re

# ── Compiled patterns ─────────────────────────────────────────────────────────

_EMAIL = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)

_PHONE = re.compile(
    r"(?<!\d)"                          # not preceded by digit
    r"(?:\+?91[\s\-]?)?"               # optional India country code
    r"(?:[6-9]\d{9}"                   # Indian mobile (10 digits starting 6-9)
    r"|\+\d{1,3}[\s\-]?\d{6,14}"      # international +XX ...
    r"|\b\d{3}[\s.\-]\d{3}[\s.\-]\d{4}\b)"  # US-style 3-3-4
    r"(?!\d)",
    re.IGNORECASE,
)

_URL = re.compile(
    r"https?://[^\s]+"
    r"|www\.[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}[^\s]*",
    re.IGNORECASE,
)

_MENTION = re.compile(r"@\w+")

_AADHAAR = re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b")


def scrub(text: str) -> str:
    """Remove PII from a review text string.

    Args:
        text: Raw review text.

    Returns:
        str: Scrubbed text with PII replaced by placeholder tokens.
    """
    if not text:
        return text
    text = _URL.sub("[URL]", text)
    text = _EMAIL.sub("[EMAIL]", text)
    text = _PHONE.sub("[PHONE]", text)
    text = _MENTION.sub("[USER]", text)
    text = _AADHAAR.sub("[ID]", text)
    return text.strip()


def scrub_review_dict(review: dict) -> dict:
    """Return a copy of a review dict with PII scrubbed from text and title.

    Args:
        review: Review dictionary (as returned by DatabaseManager).

    Returns:
        dict: New dict with scrubbed title and text fields.
    """
    scrubbed = review.copy()
    scrubbed["text"] = scrub(review.get("text", ""))
    scrubbed["title"] = scrub(review.get("title", ""))
    return scrubbed
