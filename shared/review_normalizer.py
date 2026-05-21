"""
Review normalization for Phase 1 collection.

Filters and cleans reviews before storage:
  - Minimum word count (title + body combined)
  - Remove emojis
  - English-only (non-English scripts + language detection)
"""
import re
from typing import Optional

from shared.pii_scrubber import scrub

MIN_WORD_COUNT = 6

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]+",
    flags=re.UNICODE,
)

_NON_ENGLISH_SCRIPT = re.compile(
    r"[\u0900-\u097F"  # Devanagari (Hindi)
    r"\u0980-\u09FF"   # Bengali
    r"\u0A00-\u0A7F"   # Gurmukhi
    r"\u0A80-\u0AFF"   # Gujarati
    r"\u0B00-\u0B7F"   # Oriya
    r"\u0B80-\u0BFF"   # Tamil
    r"\u0C00-\u0C7F"   # Telugu
    r"\u0C80-\u0CFF"   # Kannada
    r"\u0D00-\u0D7F"   # Malayalam
    r"\u4E00-\u9FFF"   # CJK
    r"\u3040-\u30FF"   # Japanese
    r"\uAC00-\uD7AF"   # Korean
    r"\u0600-\u06FF"   # Arabic
    r"]"
)


def remove_emojis(text: str) -> str:
    """Strip emoji characters and collapse extra whitespace."""
    if not text:
        return ""
    cleaned = _EMOJI_PATTERN.sub("", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def word_count(title: str, text: str) -> int:
    """Count words in title + body."""
    combined = f"{title} {text}".strip()
    if not combined:
        return 0
    return len(combined.split())


def has_non_english_script(text: str) -> bool:
    """True if text contains characters from common non-English scripts."""
    return bool(_NON_ENGLISH_SCRIPT.search(text))


def is_english(title: str, text: str) -> bool:
    """Return True if review content appears to be English."""
    combined = f"{title} {text}".strip()
    if not combined:
        return False

    if has_non_english_script(combined):
        return False

    try:
        from langdetect import LangDetectException, detect

        try:
            return detect(combined) == "en"
        except LangDetectException:
            letters = re.findall(r"[A-Za-z]", combined)
            return len(letters) >= MIN_WORD_COUNT
    except ImportError:
        letters = re.findall(r"[A-Za-z]", combined)
        non_ascii_alpha = re.findall(r"[^\x00-\x7F]", combined)
        return len(letters) >= MIN_WORD_COUNT and not non_ascii_alpha


def normalize_review_fields(title: str, text: str) -> Optional[tuple[str, str]]:
    """
    Scrub PII, remove emojis, and validate word count + English.

    Returns:
        (title, text) if the review passes filters, else None.
    """
    title = remove_emojis(scrub(title or ""))
    text = remove_emojis(scrub(text or ""))

    if not text:
        return None
    if word_count(title, text) < MIN_WORD_COUNT:
        return None
    if not is_english(title, text):
        return None

    return title, text
