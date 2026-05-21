"""
Tests for ReportOrchestrator — DB is real (tmp), docs client is mocked.
"""
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from report_orchestrator import ReportOrchestrator


def sample_insights_data(week="2026-W21"):
    return {
        "week": week,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_reviews_analysed": 73,
        "themes": [
            {"name": "App Crashes", "description": "Crashes on startup.",
             "review_count": 15, "sentiment": "negative", "keywords": ["crash"]},
            {"name": "Good UI", "description": "Clean interface.",
             "review_count": 20, "sentiment": "positive", "keywords": ["ui"]},
        ],
        "quotes": [
            {"text": "Crashes every time.", "theme_name": "App Crashes",
             "rating": 1, "sentiment": "negative"},
            {"text": "Love the UI!", "theme_name": "Good UI",
             "rating": 5, "sentiment": "positive"},
            {"text": "Works okay.", "theme_name": "App Crashes",
             "rating": 3, "sentiment": "neutral"},
        ],
        "actions": [
            {"description": "Fix crashes.", "priority": "high",
             "theme_name": "App Crashes", "rationale": "Many affected."},
            {"description": "Improve speed.", "priority": "medium",
             "theme_name": "Performance", "rationale": "Slow load."},
            {"description": "Add dark mode.", "priority": "low",
             "theme_name": "UI", "rationale": "Requested."},
        ],
        "sentiment_summary": {"positive": 31, "negative": 36, "neutral": 6},
        "doc_id": None,
        "email_id": None,
    }


@pytest.fixture
def orchestrator(tmp_path):
    db_path = str(tmp_path / "test.db")
    orch = ReportOrchestrator(database_path=db_path)
    # Replace docs client with a mock that always returns local_file result
    orch.docs = MagicMock()
    orch.docs.create_document.return_value = {
        "doc_id":     str(tmp_path / "report.md"),
        "doc_url":    f"file://{tmp_path}/report.md",
        "source":     "local_file",
        "title":      "Weekly Pulse — Groww — 2026-W21",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    yield orch
    orch.close()


class TestReportOrchestratorRun:

    def test_run_returns_dict(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        result = orchestrator.run(week="2026-W21")
        assert isinstance(result, dict)

    def test_run_has_required_keys(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        result = orchestrator.run(week="2026-W21")
        for key in ("week", "doc_id", "doc_url", "source", "word_count", "report"):
            assert key in result

    def test_run_correct_week(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data("2026-W21"))
        result = orchestrator.run(week="2026-W21")
        assert result["week"] == "2026-W21"

    def test_run_word_count_within_limit(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        result = orchestrator.run(week="2026-W21")
        assert result["word_count"] <= 250

    def test_run_doc_id_saved_to_db(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        result = orchestrator.run(week="2026-W21")
        stored = orchestrator.db.get_insights("2026-W21")
        assert stored["doc_id"] == result["doc_id"]

    def test_run_calls_create_document(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        orchestrator.run(week="2026-W21")
        orchestrator.docs.create_document.assert_called_once()

    def test_run_passes_title_to_docs(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        orchestrator.run(week="2026-W21")
        call_args = orchestrator.docs.create_document.call_args
        title = call_args[1].get("title") or call_args[0][0]
        assert "2026-W21" in title

    def test_run_raises_if_no_insights(self, orchestrator):
        with pytest.raises(ValueError, match="No insights found"):
            orchestrator.run(week="9999-W99")

    def test_run_report_has_all_sections(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        result = orchestrator.run(week="2026-W21")
        sections = result["report"]["sections"]
        for key in ("header", "sentiment", "themes", "quotes", "actions", "footer"):
            assert key in sections

    def test_run_report_contains_themes(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        result = orchestrator.run(week="2026-W21")
        plain = result["report"]["plain_text"]
        assert "App Crashes" in plain
        assert "Good UI" in plain

    def test_run_report_contains_quotes(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        result = orchestrator.run(week="2026-W21")
        plain = result["report"]["plain_text"]
        assert "Crashes every time" in plain

    def test_run_report_contains_actions(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        result = orchestrator.run(week="2026-W21")
        plain = result["report"]["plain_text"]
        assert "Fix crashes" in plain

    def test_run_uses_latest_when_week_not_specified(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data("2026-W21"))
        result = orchestrator.run()   # no week arg
        assert result["week"] == "2026-W21"


class TestDictToInsights:

    def test_converts_themes(self, orchestrator):
        data = sample_insights_data()
        insights = orchestrator._dict_to_insights(data)
        assert len(insights.themes) == 2
        assert insights.themes[0].name == "App Crashes"

    def test_converts_quotes(self, orchestrator):
        data = sample_insights_data()
        insights = orchestrator._dict_to_insights(data)
        assert len(insights.quotes) == 3

    def test_converts_actions(self, orchestrator):
        data = sample_insights_data()
        insights = orchestrator._dict_to_insights(data)
        assert len(insights.actions) == 3

    def test_converts_sentiment_summary(self, orchestrator):
        data = sample_insights_data()
        insights = orchestrator._dict_to_insights(data)
        assert insights.sentiment_summary["positive"] == 31

    def test_handles_empty_themes(self, orchestrator):
        data = sample_insights_data()
        data["themes"] = []
        insights = orchestrator._dict_to_insights(data)
        assert insights.themes == []
