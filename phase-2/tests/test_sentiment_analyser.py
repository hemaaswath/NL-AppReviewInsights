"""
Tests for SentimentAnalyser — all LLM calls are mocked.
"""
import pytest
from unittest.mock import MagicMock, patch
from shared.models import SentimentLabel, ReviewSentiment
from sentiment_analyser import SentimentAnalyser


def make_llm_response(sentiment="negative", confidence=0.95, reasoning="Test"):
    import json
    mock = MagicMock()
    mock.content = json.dumps({
        "sentiment": sentiment,
        "confidence": confidence,
        "reasoning": reasoning,
    })
    return mock


@pytest.fixture
def analyser():
    with patch("sentiment_analyser.ChatGroq"):
        a = SentimentAnalyser()
        a.llm = MagicMock()
        return a


class TestSentimentAnalyserSingle:

    def test_returns_review_sentiment_object(self, analyser):
        analyser.llm.invoke.return_value = make_llm_response("negative")
        result = analyser.analyse("r1", "App crashes constantly", 1)
        assert isinstance(result, ReviewSentiment)

    def test_review_id_preserved(self, analyser):
        analyser.llm.invoke.return_value = make_llm_response("negative")
        result = analyser.analyse("my-id-123", "Bad app", 1)
        assert result.review_id == "my-id-123"

    def test_positive_sentiment_parsed(self, analyser):
        analyser.llm.invoke.return_value = make_llm_response("positive", 0.98)
        result = analyser.analyse("r2", "Love this app!", 5)
        assert result.sentiment == SentimentLabel.POSITIVE
        assert result.confidence == 0.98

    def test_negative_sentiment_parsed(self, analyser):
        analyser.llm.invoke.return_value = make_llm_response("negative", 0.92)
        result = analyser.analyse("r3", "Terrible, keeps crashing", 1)
        assert result.sentiment == SentimentLabel.NEGATIVE

    def test_neutral_sentiment_parsed(self, analyser):
        analyser.llm.invoke.return_value = make_llm_response("neutral", 0.70)
        result = analyser.analyse("r4", "It works, nothing special", 3)
        assert result.sentiment == SentimentLabel.NEUTRAL

    def test_confidence_in_range(self, analyser):
        analyser.llm.invoke.return_value = make_llm_response("positive", 0.85)
        result = analyser.analyse("r5", "Great app", 5)
        assert 0.0 <= result.confidence <= 1.0

    def test_fallback_on_llm_error_high_rating(self, analyser):
        analyser.llm.invoke.side_effect = Exception("API error")
        result = analyser.analyse("r6", "Some text", 5)
        assert result.sentiment == SentimentLabel.POSITIVE
        assert result.confidence == 0.6

    def test_fallback_on_llm_error_low_rating(self, analyser):
        analyser.llm.invoke.side_effect = Exception("API error")
        result = analyser.analyse("r7", "Some text", 1)
        assert result.sentiment == SentimentLabel.NEGATIVE

    def test_fallback_on_llm_error_mid_rating(self, analyser):
        analyser.llm.invoke.side_effect = Exception("API error")
        result = analyser.analyse("r8", "Some text", 3)
        assert result.sentiment == SentimentLabel.NEUTRAL

    def test_handles_markdown_fenced_json(self, analyser):
        import json
        mock = MagicMock()
        mock.content = "```json\n" + json.dumps({
            "sentiment": "positive", "confidence": 0.9, "reasoning": "Good"
        }) + "\n```"
        analyser.llm.invoke.return_value = mock
        result = analyser.analyse("r9", "Great", 5)
        assert result.sentiment == SentimentLabel.POSITIVE


class TestSentimentAnalyserBatch:

    def test_batch_returns_list(self, analyser):
        analyser.llm.invoke.return_value = make_llm_response("negative")
        reviews = [{"id": f"r{i}", "text": f"Review {i}", "rating": 2} for i in range(5)]
        results = analyser.analyse_batch(reviews)
        assert isinstance(results, list)
        assert len(results) == 5

    def test_batch_all_have_review_ids(self, analyser):
        analyser.llm.invoke.return_value = make_llm_response("positive")
        reviews = [{"id": f"id-{i}", "text": "Good", "rating": 5} for i in range(3)]
        results = analyser.analyse_batch(reviews)
        ids = [r.review_id for r in results]
        assert ids == ["id-0", "id-1", "id-2"]

    def test_empty_batch_returns_empty(self, analyser):
        results = analyser.analyse_batch([])
        assert results == []

    def test_batch_known_sentiments(self, analyser):
        """Positive reviews → positive, negative → negative."""
        import json
        def side_effect(messages):
            text = messages[1].content
            if "rating: 5" in text.lower() or "5/5" in text:
                return MagicMock(content=json.dumps({"sentiment": "positive", "confidence": 0.9, "reasoning": ""}))
            return MagicMock(content=json.dumps({"sentiment": "negative", "confidence": 0.9, "reasoning": ""}))

        analyser.llm.invoke.side_effect = side_effect
        reviews = [
            {"id": "pos", "text": "Amazing app", "rating": 5},
            {"id": "neg", "text": "Terrible crashes", "rating": 1},
        ]
        results = analyser.analyse_batch(reviews)
        sentiments = {r.review_id: r.sentiment for r in results}
        assert sentiments["pos"] == SentimentLabel.POSITIVE
        assert sentiments["neg"] == SentimentLabel.NEGATIVE
