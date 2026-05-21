"""
Tests for ThemeClusterer — all LLM calls are mocked.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from shared.models import Theme, SentimentLabel
from theme_clusterer import ThemeClusterer


def make_themes_response(themes: list[dict]) -> MagicMock:
    mock = MagicMock()
    mock.content = json.dumps(themes)
    return mock


SAMPLE_THEMES = [
    {"name": "App Crashes", "description": "App crashes on startup.", "review_count": 20,
     "sentiment": "negative", "keywords": ["crash", "freeze", "bug"]},
    {"name": "Good UI", "description": "Users love the interface.", "review_count": 15,
     "sentiment": "positive", "keywords": ["ui", "design", "clean"]},
]


@pytest.fixture
def clusterer():
    with patch("theme_clusterer.ChatGroq"):
        c = ThemeClusterer()
        c.llm = MagicMock()
        return c


def make_reviews(n=10):
    return [{"id": f"r{i}", "text": f"Review text {i}", "rating": (i % 5) + 1} for i in range(n)]


class TestThemeClustererBasic:

    def test_returns_list_of_themes(self, clusterer):
        clusterer.llm.invoke.return_value = make_themes_response(SAMPLE_THEMES)
        result = clusterer.cluster(make_reviews())
        assert isinstance(result, list)
        assert all(isinstance(t, Theme) for t in result)

    def test_max_5_themes_enforced(self, clusterer):
        many_themes = [
            {"name": f"Theme {i}", "description": "Desc", "review_count": 5,
             "sentiment": "neutral", "keywords": ["kw"]}
            for i in range(8)
        ]
        clusterer.llm.invoke.return_value = make_themes_response(many_themes)
        result = clusterer.cluster(make_reviews())
        assert len(result) <= 5

    def test_theme_fields_populated(self, clusterer):
        clusterer.llm.invoke.return_value = make_themes_response(SAMPLE_THEMES)
        result = clusterer.cluster(make_reviews())
        t = result[0]
        assert t.name == "App Crashes"
        assert t.review_count == 20
        assert t.sentiment == SentimentLabel.NEGATIVE
        assert "crash" in t.keywords

    def test_empty_reviews_returns_empty(self, clusterer):
        result = clusterer.cluster([])
        assert result == []

    def test_fallback_on_llm_error(self, clusterer):
        clusterer.llm.invoke.side_effect = Exception("API error")
        result = clusterer.cluster(make_reviews())
        assert len(result) == 1
        assert result[0].name == "General Feedback"

    def test_handles_markdown_fenced_json(self, clusterer):
        mock = MagicMock()
        mock.content = "```json\n" + json.dumps(SAMPLE_THEMES) + "\n```"
        clusterer.llm.invoke.return_value = mock
        result = clusterer.cluster(make_reviews())
        assert len(result) == 2

    def test_single_review_still_works(self, clusterer):
        clusterer.llm.invoke.return_value = make_themes_response(SAMPLE_THEMES[:1])
        result = clusterer.cluster([{"id": "r1", "text": "Crashes", "rating": 1}])
        assert len(result) >= 1

    def test_themes_have_valid_sentiment(self, clusterer):
        clusterer.llm.invoke.return_value = make_themes_response(SAMPLE_THEMES)
        result = clusterer.cluster(make_reviews())
        for t in result:
            assert t.sentiment in list(SentimentLabel)

    def test_review_digest_truncates_long_text(self, clusterer):
        """Long review text is truncated in the prompt (no token overflow)."""
        long_reviews = [{"id": "r1", "text": "x" * 1000, "rating": 3}]
        clusterer.llm.invoke.return_value = make_themes_response(SAMPLE_THEMES[:1])
        result = clusterer.cluster(long_reviews)
        assert len(result) >= 1
        # Verify the prompt sent to LLM was truncated
        call_args = clusterer.llm.invoke.call_args
        prompt_text = call_args[0][0][1].content
        assert len(prompt_text) < 5000  # well under token limit
