"""
Tests for AnalysisOrchestrator — DB and all LLM components are mocked.
"""
import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone
from shared.models import (
    WeeklyInsights, Theme, Quote, ActionItem, SentimentLabel, ReviewSentiment
)
from analysis_orchestrator import AnalysisOrchestrator, _current_week


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_reviews(n=5):
    return [
        {"id": f"r{i}", "source": "google_play", "rating": (i % 5) + 1,
         "title": f"Title {i}", "text": f"Review text {i}", "date": "2026-01-01",
         "version": "1.0", "processed": False}
        for i in range(n)
    ]


def make_themes():
    return [
        Theme(name="App Crashes", description="Crashes.", review_count=3,
              sentiment=SentimentLabel.NEGATIVE, keywords=["crash"]),
    ]


def make_quotes():
    return [
        Quote(text="Crashes every time.", theme_name="App Crashes",
              rating=1, sentiment=SentimentLabel.NEGATIVE),
        Quote(text="Love the UI.", theme_name="Good UI",
              rating=5, sentiment=SentimentLabel.POSITIVE),
        Quote(text="Okay app.", theme_name="App Crashes",
              rating=3, sentiment=SentimentLabel.NEUTRAL),
    ]


def make_actions():
    return [
        ActionItem(description="Fix crashes.", priority="high",
                   theme_name="App Crashes", rationale="Many users affected."),
        ActionItem(description="Improve speed.", priority="medium",
                   theme_name="Performance", rationale="Slow load times."),
        ActionItem(description="Add dark mode.", priority="low",
                   theme_name="UI", rationale="Requested feature."),
    ]


def make_sentiments(reviews):
    return [
        ReviewSentiment(review_id=r["id"], sentiment=SentimentLabel.NEGATIVE,
                        confidence=0.9, reasoning="Low rating")
        for r in reviews
    ]


@pytest.fixture
def orchestrator(tmp_path):
    """Orchestrator with real temp DB but mocked LLM components."""
    db_path = str(tmp_path / "test.db")
    with patch("analysis_orchestrator.SentimentAnalyser") as MockSA, \
         patch("analysis_orchestrator.ThemeClusterer") as MockTC, \
         patch("analysis_orchestrator.QuoteExtractor") as MockQE, \
         patch("analysis_orchestrator.ActionGenerator") as MockAG:

        orch = AnalysisOrchestrator(database_path=db_path)

        # Wire up mock return values
        orch.sentiment_analyser = MagicMock()
        orch.theme_clusterer = MagicMock()
        orch.quote_extractor = MagicMock()
        orch.action_generator = MagicMock()

        yield orch
        orch.close()


class TestCurrentWeek:
    def test_returns_iso_week_format(self):
        week = _current_week()
        assert "-W" in week
        parts = week.split("-W")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1].isdigit()


class TestAnalysisOrchestratorRun:

    def _setup_mocks(self, orch, reviews):
        orch.sentiment_analyser.analyse_batch.return_value = make_sentiments(reviews)
        orch.theme_clusterer.cluster.return_value = make_themes()
        orch.quote_extractor.extract.return_value = make_quotes()
        orch.action_generator.generate.return_value = make_actions()

    def test_run_returns_weekly_insights(self, orchestrator):
        reviews = make_reviews(5)
        orchestrator.db.save_reviews_batch(reviews)
        self._setup_mocks(orchestrator, reviews)
        result = orchestrator.run(week="2026-W20", mark_processed=False)
        assert isinstance(result, WeeklyInsights)

    def test_run_correct_week(self, orchestrator):
        reviews = make_reviews(3)
        orchestrator.db.save_reviews_batch(reviews)
        self._setup_mocks(orchestrator, reviews)
        result = orchestrator.run(week="2026-W99", mark_processed=False)
        assert result.week == "2026-W99"

    def test_run_total_reviews_analysed(self, orchestrator):
        reviews = make_reviews(5)
        orchestrator.db.save_reviews_batch(reviews)
        self._setup_mocks(orchestrator, reviews)
        result = orchestrator.run(week="2026-W20", mark_processed=False)
        assert result.total_reviews_analysed == 5

    def test_run_themes_present(self, orchestrator):
        reviews = make_reviews(5)
        orchestrator.db.save_reviews_batch(reviews)
        self._setup_mocks(orchestrator, reviews)
        result = orchestrator.run(week="2026-W20", mark_processed=False)
        assert len(result.themes) >= 1
        assert isinstance(result.themes[0], Theme)

    def test_run_quotes_present(self, orchestrator):
        reviews = make_reviews(5)
        orchestrator.db.save_reviews_batch(reviews)
        self._setup_mocks(orchestrator, reviews)
        result = orchestrator.run(week="2026-W20", mark_processed=False)
        assert len(result.quotes) == 3

    def test_run_actions_present(self, orchestrator):
        reviews = make_reviews(5)
        orchestrator.db.save_reviews_batch(reviews)
        self._setup_mocks(orchestrator, reviews)
        result = orchestrator.run(week="2026-W20", mark_processed=False)
        assert len(result.actions) == 3

    def test_run_sentiment_summary_populated(self, orchestrator):
        reviews = make_reviews(5)
        orchestrator.db.save_reviews_batch(reviews)
        self._setup_mocks(orchestrator, reviews)
        result = orchestrator.run(week="2026-W20", mark_processed=False)
        assert "positive" in result.sentiment_summary
        assert "negative" in result.sentiment_summary
        assert "neutral" in result.sentiment_summary

    def test_run_marks_reviews_processed(self, orchestrator):
        reviews = make_reviews(3)
        orchestrator.db.save_reviews_batch(reviews)
        self._setup_mocks(orchestrator, reviews)
        orchestrator.run(week="2026-W20", mark_processed=True)
        unprocessed = orchestrator.db.get_unprocessed_reviews()
        assert len(unprocessed) == 0

    def test_run_saves_insights_to_db(self, orchestrator):
        reviews = make_reviews(3)
        orchestrator.db.save_reviews_batch(reviews)
        self._setup_mocks(orchestrator, reviews)
        orchestrator.run(week="2026-W20", mark_processed=False)
        stored = orchestrator.db.get_insights("2026-W20")
        assert stored is not None
        assert stored["week"] == "2026-W20"

    def test_run_empty_db_returns_empty_insights(self, orchestrator):
        self._setup_mocks(orchestrator, [])
        result = orchestrator.run(week="2026-W20", mark_processed=False)
        assert isinstance(result, WeeklyInsights)
        assert result.total_reviews_analysed == 0

    def test_run_max_reviews_respected(self, orchestrator):
        reviews = make_reviews(10)
        orchestrator.db.save_reviews_batch(reviews)
        self._setup_mocks(orchestrator, reviews[:3])
        orchestrator.run(week="2026-W20", max_reviews=3, mark_processed=False)
        call_args = orchestrator.sentiment_analyser.analyse_batch.call_args
        assert len(call_args[0][0]) <= 3


class TestAnalysisOrchestratorInsightsRetrieval:

    def _run_and_store(self, orchestrator, week="2026-W20"):
        reviews = make_reviews(3)
        orchestrator.db.save_reviews_batch(reviews)
        orchestrator.sentiment_analyser.analyse_batch.return_value = make_sentiments(reviews)
        orchestrator.theme_clusterer.cluster.return_value = make_themes()
        orchestrator.quote_extractor.extract.return_value = make_quotes()
        orchestrator.action_generator.generate.return_value = make_actions()
        orchestrator.run(week=week, mark_processed=False)

    def test_get_insights_json_returns_string(self, orchestrator):
        self._run_and_store(orchestrator)
        result = orchestrator.get_insights_json("2026-W20")
        assert isinstance(result, str)
        data = json.loads(result)
        assert data["week"] == "2026-W20"

    def test_get_insights_json_missing_week(self, orchestrator):
        result = orchestrator.get_insights_json("9999-W99")
        data = json.loads(result)
        assert "error" in data

    def test_get_insights_json_latest(self, orchestrator):
        self._run_and_store(orchestrator, "2026-W20")
        result = orchestrator.get_insights_json()
        data = json.loads(result)
        assert data["week"] == "2026-W20"


class TestInsightsDBMethods:
    """Direct tests for DatabaseManager insights methods."""

    @pytest.fixture
    def db(self, tmp_path):
        from shared.database import DatabaseManager
        d = DatabaseManager(str(tmp_path / "test.db"))
        yield d
        d.close()

    def _sample_insights(self, week="2026-W20"):
        return {
            "week": week,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_reviews_analysed": 10,
            "themes": [{"name": "Crashes", "description": "App crashes", "review_count": 5,
                        "sentiment": "negative", "keywords": ["crash"]}],
            "quotes": [{"text": "Crashes!", "theme_name": "Crashes", "rating": 1, "sentiment": "negative"}],
            "actions": [{"description": "Fix crashes", "priority": "high",
                         "theme_name": "Crashes", "rationale": "Many affected"}],
            "sentiment_summary": {"positive": 2, "negative": 7, "neutral": 1},
            "doc_id": None,
            "email_id": None,
        }

    def test_save_and_retrieve_insights(self, db):
        db.save_insights(self._sample_insights("2026-W20"))
        result = db.get_insights("2026-W20")
        assert result is not None
        assert result["week"] == "2026-W20"
        assert result["total_reviews_analysed"] == 10

    def test_get_latest_insights(self, db):
        db.save_insights(self._sample_insights("2026-W18"))
        db.save_insights(self._sample_insights("2026-W20"))
        result = db.get_insights()
        assert result["week"] == "2026-W20"

    def test_update_existing_insights(self, db):
        db.save_insights(self._sample_insights("2026-W20"))
        updated = self._sample_insights("2026-W20")
        updated["total_reviews_analysed"] = 99
        db.save_insights(updated)
        result = db.get_insights("2026-W20")
        assert result["total_reviews_analysed"] == 99

    def test_get_nonexistent_week_returns_none(self, db):
        assert db.get_insights("9999-W99") is None

    def test_list_insights_weeks(self, db):
        db.save_insights(self._sample_insights("2026-W18"))
        db.save_insights(self._sample_insights("2026-W20"))
        weeks = db.list_insights_weeks()
        assert "2026-W18" in weeks
        assert "2026-W20" in weeks

    def test_themes_stored_as_json(self, db):
        db.save_insights(self._sample_insights("2026-W20"))
        result = db.get_insights("2026-W20")
        assert isinstance(result["themes"], list)
        assert result["themes"][0]["name"] == "Crashes"

    def test_sentiment_summary_stored(self, db):
        db.save_insights(self._sample_insights("2026-W20"))
        result = db.get_insights("2026-W20")
        assert result["sentiment_summary"]["negative"] == 7
