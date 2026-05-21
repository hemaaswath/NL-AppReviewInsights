"""
Simple spacing between Groq API calls to respect RPM limits.
"""
import time

from shared.phase2_config import GROQ_MIN_INTERVAL_SEC

_last_call_at: float = 0.0


def wait_for_groq_slot() -> None:
    """Sleep if needed so consecutive calls stay under GROQ_RPM."""
    global _last_call_at
    now = time.monotonic()
    elapsed = now - _last_call_at
    if _last_call_at > 0 and elapsed < GROQ_MIN_INTERVAL_SEC:
        time.sleep(GROQ_MIN_INTERVAL_SEC - elapsed)
    _last_call_at = time.monotonic()


def reset_groq_throttle() -> None:
    """Reset throttle clock (for tests)."""
    global _last_call_at
    _last_call_at = 0.0
