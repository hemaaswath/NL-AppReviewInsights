"""
Tests for ActionGenerator — all LLM calls are mocked.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from shared.models import ActionItem, Theme, Quote, SentimentLabel
from action_generator import ActionGenerator


def make_actions_response(actions: list[dict]) -> MagicMock:
    mock = MagicMock()
    mock.content = json.dumps(actions)
    return mock


SAMPLE_THEMES = [
    Theme(name="App Crashes", description="Crashes on startup.", review_count=20,
          sentiment=SentimentLabel.NEGATIVE, keywords=["crash"]),
    Theme(name="Slow Performance", description="App is slow.", review_count=10,
          sentiment=SentimentLabel.NEGATIVE, keywords=["slow", "lag"]),
]

SAMPLE_QUOTES = [
    Quote(text="Crashes every time.", theme_name="App Crashes", rating=1, sentiment=SentimentLabel.NEGATIVE),
    Quote(text="Very slow to load.", theme_name="Slow Performance", rating=2, sentiment=SentimentLabel.NEGATIVE),
    Quote(text="Love the UI.", theme_name="Good UI", rating=5, sentiment=SentimentLabel.POSITIVE),
]

SAMPLE_ACTIONS = [
    {"description": "Fix crash on portfolio screen.", "priority": "high",
     "theme_name": "App Crashes", "rationale": "20 users report crashes."},
    {"description": "Optimise data loading with caching.", "priority": "medium",
     "theme_name": "Slow Performance", "rationale": "Users report 5-10s load times."},
    {"description": "Add dark mode support.", "priority": "low",
     "theme_name": "UI Requests", "rationale": "Frequently requested feature."},
]

SENTIMENT_SUMMARY = {"positive": 10, "negative": 50, "neutral": 13}


@pytest.fixture
def generator():
    with patch("action_generator.ChatGroq"):
        g = ActionGenerator()
        g.llm = MagicMock()
        return g


class TestActionGeneratorBasic:

    def test_returns_list_of_action_items(self, generator):
        generator.llm.invoke.return_value = make_actions_response(SAMPLE_ACTIONS)
        result = generator.generate(SAMPLE_THEMES, SAMPLE_QUOTES, SENTIMENT_SUMMARY)
        assert isinstance(result, list)
        assert all(isinstance(a, ActionItem) for a in result)

    def test_exactly_3_actions_returned(self, generator):
        generator.llm.invoke.return_value = make_actions_response(SAMPLE_ACTIONS)
        result = generator.generate(SAMPLE_THEMES, SAMPLE_QUOTES, SENTIMENT_SUMMARY)
        assert len(result) == 3

    def test_action_fields_populated(self, generator):
        generator.llm.invoke.return_value = make_actions_response(SAMPLE_ACTIONS)
        result = generator.generate(SAMPLE_THEMES, SAMPLE_QUOTES, SENTIMENT_SUMMARY)
        a = result[0]
        assert a.description == "Fix crash on portfolio screen."
        assert a.priority == "high"
        assert a.theme_name == "App Crashes"
        assert "20 users" in a.rationale

    def test_priority_values_valid(self, generator):
        generator.llm.invoke.return_value = make_actions_response(SAMPLE_ACTIONS)
        result = generator.generate(SAMPLE_THEMES, SAMPLE_QUOTES, SENTIMENT_SUMMARY)
        for a in result:
            assert a.priority in ("high", "medium", "low")

    def test_fallback_on_empty_themes(self, generator):
        result = generator.generate([], [], {})
        assert len(result) == 3
        assert all(isinstance(a, ActionItem) for a in result)

    def test_fallback_on_llm_error(self, generator):
        generator.llm.invoke.side_effect = Exception("API error")
        result = generator.generate(SAMPLE_THEMES, SAMPLE_QUOTES, SENTIMENT_SUMMARY)
        assert len(result) == 3
        assert all(isinstance(a, ActionItem) for a in result)

    def test_handles_markdown_fenced_json(self, generator):
        mock = MagicMock()
        mock.content = "```json\n" + json.dumps(SAMPLE_ACTIONS) + "\n```"
        generator.llm.invoke.return_value = mock
        result = generator.generate(SAMPLE_THEMES, SAMPLE_QUOTES, SENTIMENT_SUMMARY)
        assert len(result) == 3

    def test_pads_to_3_if_llm_returns_fewer(self, generator):
        generator.llm.invoke.return_value = make_actions_response(SAMPLE_ACTIONS[:1])
        result = generator.generate(SAMPLE_THEMES, SAMPLE_QUOTES, SENTIMENT_SUMMARY)
        assert len(result) == 3

    def test_caps_at_3_if_llm_returns_more(self, generator):
        many = SAMPLE_ACTIONS * 3
        generator.llm.invoke.return_value = make_actions_response(many)
        result = generator.generate(SAMPLE_THEMES, SAMPLE_QUOTES, SENTIMENT_SUMMARY)
        assert len(result) == 3

    def test_high_negative_pct_reflected_in_prompt(self, generator):
        generator.llm.invoke.return_value = make_actions_response(SAMPLE_ACTIONS)
        generator.generate(SAMPLE_THEMES, SAMPLE_QUOTES, {"positive": 5, "negative": 95, "neutral": 0})
        call_args = generator.llm.invoke.call_args
        prompt = call_args[0][0][1].content
        assert "95%" in prompt
