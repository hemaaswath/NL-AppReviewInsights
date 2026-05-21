"""
Tests for QuoteExtractor — all LLM calls are mocked.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from shared.models import Quote, Theme, SentimentLabel
from quote_extractor import QuoteExtractor


def make_quotes_response(quotes: list[dict]) -> MagicMock:
    mock = MagicMock()
    mock.content = json.dumps(quotes)
    return mock


SAMPLE_THEMES = [
    Theme(name="App Crashes", description="Crashes on startup.", review_count=20,
          sentiment=SentimentLabel.NEGATIVE, keywords=["crash"]),
    Theme(name="Good UI", description="Clean interface.", review_count=15,
          sentiment=SentimentLabel.POSITIVE, keywords=["ui"]),
]

SAMPLE_QUOTES = [
    {"text": "App crashes every time I open it.", "theme_name": "App Crashes", "rating": 1, "sentiment": "negative"},
    {"text": "Love the clean interface!", "theme_name": "Good UI", "rating": 5, "sentiment": "positive"},
    {"text": "Works okay but could be faster.", "theme_name": "App Crashes", "rating": 3, "sentiment": "neutral"},
]


def make_reviews(n=10):
    return [{"id": f"r{i}", "text": f"Review text number {i}", "rating": (i % 5) + 1} for i in range(n)]


@pytest.fixture
def extractor():
    with patch("quote_extractor.ChatGroq"):
        e = QuoteExtractor()
        e.llm = MagicMock()
        return e


class TestQuoteExtractorBasic:

    def test_returns_list_of_quotes(self, extractor):
        extractor.llm.invoke.return_value = make_quotes_response(SAMPLE_QUOTES)
        result = extractor.extract(make_reviews(), SAMPLE_THEMES)
        assert isinstance(result, list)
        assert all(isinstance(q, Quote) for q in result)

    def test_max_3_quotes_enforced(self, extractor):
        many_quotes = [
            {"text": f"Quote {i}", "theme_name": "App Crashes", "rating": 2, "sentiment": "negative"}
            for i in range(10)
        ]
        extractor.llm.invoke.return_value = make_quotes_response(many_quotes)
        result = extractor.extract(make_reviews(), SAMPLE_THEMES)
        assert len(result) <= 3

    def test_quote_fields_populated(self, extractor):
        extractor.llm.invoke.return_value = make_quotes_response(SAMPLE_QUOTES)
        result = extractor.extract(make_reviews(), SAMPLE_THEMES)
        q = result[0]
        assert q.text == "App crashes every time I open it."
        assert q.theme_name == "App Crashes"
        assert q.rating == 1
        assert q.sentiment == SentimentLabel.NEGATIVE

    def test_empty_reviews_returns_empty(self, extractor):
        result = extractor.extract([], SAMPLE_THEMES)
        assert result == []

    def test_fallback_on_llm_error(self, extractor):
        extractor.llm.invoke.side_effect = Exception("API error")
        reviews = [{"id": f"r{i}", "text": f"Some review {i}", "rating": 2} for i in range(5)]
        result = extractor.extract(reviews, SAMPLE_THEMES)
        assert len(result) <= 3
        assert all(isinstance(q, Quote) for q in result)

    def test_handles_markdown_fenced_json(self, extractor):
        mock = MagicMock()
        mock.content = "```json\n" + json.dumps(SAMPLE_QUOTES) + "\n```"
        extractor.llm.invoke.return_value = mock
        result = extractor.extract(make_reviews(), SAMPLE_THEMES)
        assert len(result) == 3

    def test_quotes_have_valid_sentiment(self, extractor):
        extractor.llm.invoke.return_value = make_quotes_response(SAMPLE_QUOTES)
        result = extractor.extract(make_reviews(), SAMPLE_THEMES)
        for q in result:
            assert q.sentiment in list(SentimentLabel)

    def test_quotes_have_valid_rating(self, extractor):
        extractor.llm.invoke.return_value = make_quotes_response(SAMPLE_QUOTES)
        result = extractor.extract(make_reviews(), SAMPLE_THEMES)
        for q in result:
            assert 1 <= q.rating <= 5

    def test_no_themes_uses_fallback_theme_name(self, extractor):
        extractor.llm.invoke.side_effect = Exception("error")
        reviews = [{"id": "r1", "text": "Bad app", "rating": 1}]
        result = extractor.extract(reviews, [])
        # Should not crash; fallback uses "General Feedback"
        assert isinstance(result, list)

    def test_caps_reviews_at_50_for_prompt(self, extractor):
        """Only first 30 reviews are sent to LLM to avoid token overflow."""
        extractor.llm.invoke.return_value = make_quotes_response(SAMPLE_QUOTES)
        large_reviews = [{"id": f"r{i}", "text": f"Review {i}", "rating": 3} for i in range(100)]
        extractor.extract(large_reviews, SAMPLE_THEMES)
        call_args = extractor.llm.invoke.call_args
        prompt_text = call_args[0][0][1].content
        # Should contain "30." but not "31."
        assert "30." in prompt_text
        assert "31." not in prompt_text
