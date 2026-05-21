"""
Tests for Phase 1 review normalization.
"""
import pytest

from shared.review_normalizer import (
    MIN_WORD_COUNT,
    is_english,
    normalize_review_fields,
    remove_emojis,
    word_count,
)


class TestRemoveEmojis:
    def test_strips_common_emoji(self):
        assert remove_emojis("Great app 🎉 love it") == "Great app love it"

    def test_empty_string(self):
        assert remove_emojis("") == ""


class TestWordCount:
    def test_counts_title_and_body(self):
        assert word_count("One two", "three four five six") == 6

    def test_below_minimum(self):
        assert word_count("", "too short review") < MIN_WORD_COUNT


class TestNormalizeReviewFields:
    def test_accepts_valid_english_review(self):
        title = "Good app"
        text = "This investment app works well for beginners and experts alike."
        result = normalize_review_fields(title, text)
        assert result is not None
        assert "investment" in result[1]

    def test_rejects_short_review(self):
        assert normalize_review_fields("", "Only five words here now") is None

    def test_rejects_hindi_script(self):
        text = "यह ऐप बहुत अच्छा है और मुझे पसंद आया है क्योंकि यह आसान है"
        assert normalize_review_fields("", text) is None

    def test_strips_emojis_from_long_review(self):
        text = "This is a good investment app for beginners " + "🎉🔥✨"
        result = normalize_review_fields("", text)
        assert result is not None
        assert "🎉" not in result[1]

    def test_scrubs_pii_and_keeps_review(self):
        text = (
            "Contact support at user@example.com for help with my account "
            "balance and trading issues today please."
        )
        result = normalize_review_fields("", text)
        assert result is not None
        assert "[EMAIL]" in result[1]
        assert "user@example.com" not in result[1]


class TestIsEnglish:
    def test_english_detected(self):
        assert is_english("", "The app crashes when I open the mutual fund section.")

    def test_non_english_script_rejected(self):
        assert not is_english("", "இது ஒரு சோதனை விமர்சனம் மட்டுமே போதும் என்று நினைக்கிறேன்")
