"""
Extended corner-case tests for ReportOrchestrator.
"""
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from report_orchestrator import ReportOrchestrator


def make_doc_result(tmp_path, week="2026-W21"):
    return {
        "doc_id":     str(tmp_path / f"report_{week}.md"),
        "doc_url":    f"file://{tmp_path}/report_{week}.md",
        "source":     "local_file",
        "title":      f"Weekly Pulse — Groww — {week}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def sample_data(week="2026-W21", doc_id=None, **overrides):
    data = {
        "week": week,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_reviews_analysed": 10,
        "themes": [
            {"name": "Crashes", "description": "App crashes.",
             "review_count": 5, "sentiment": "negative", "keywords": ["crash"]},
        ],
        "quotes": [
            {"text": "Crashes.", "theme_name": "Crashes", "rating": 1, "sentiment": "negative"},
            {"text": "Okay.", "theme_name": "Crashes", "rating": 3, "sentiment": "neutral"},
            {"text": "Good.", "theme_name": "Crashes", "rating": 5, "sentiment": "positive"},
        ],
        "actions": [
            {"description": "Fix it.", "priority": "high",
             "theme_name": "Crashes", "rationale": "Many affected."},
            {"description": "Speed up.", "priority": "medium",
             "theme_name": "Speed", "rationale": "Slow."},
            {"description": "Dark mode.", "priority": "low",
             "theme_name": "UI", "rationale": "Requested."},
        ],
        "sentiment_summary": {"positive": 3, "negative": 5, "neutral": 2},
        "doc_id": doc_id,
        "email_id": None,
    }
    data.update(overrides)
    return data


@pytest.fixture
def orch(tmp_path):
    db_path = str(tmp_path / "test.db")
    o = ReportOrchestrator(database_path=db_path)
    o.docs = MagicMock()
    o.docs.create_document.side_effect = lambda title, content: make_doc_result(tmp_path)
    yield o
    o.close()


# ── Re-run / idempotency ──────────────────────────────────────────────────────

class TestReRunBehaviour:

    def test_rerun_overwrites_doc_id(self, orch, tmp_path):
        """Running Phase 3 twice for the same week updates doc_id."""
        orch.db.save_insights(sample_data(doc_id="old-doc-id"))
        orch.docs.create_document.side_effect = lambda title, content: {
            "doc_id": "new-doc-id", "doc_url": "file://new",
            "source": "local_file", "title": title,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = orch.run(week="2026-W21")
        stored = orch.db.get_insights("2026-W21")
        assert stored["doc_id"] == "new-doc-id"
        assert result["doc_id"] == "new-doc-id"

    def test_rerun_does_not_duplicate_insights(self, orch):
        """Running twice should not create duplicate DB rows."""
        orch.db.save_insights(sample_data())
        orch.run(week="2026-W21")
        orch.run(week="2026-W21")
        weeks = orch.db.list_insights_weeks()
        assert weeks.count("2026-W21") == 1

    def test_run_preserves_email_id(self, orch):
        """email_id set by Phase 4 should not be wiped by Phase 3 re-run."""
        data = sample_data(email_id="gmail-draft-123")
        orch.db.save_insights(data)
        orch.run(week="2026-W21")
        stored = orch.db.get_insights("2026-W21")
        assert stored["email_id"] == "gmail-draft-123"


# ── Empty / minimal insights ──────────────────────────────────────────────────

class TestMinimalInsights:

    def test_no_themes_no_quotes_no_actions(self, orch):
        """Insights with empty lists should not crash."""
        orch.db.save_insights(sample_data(themes=[], quotes=[], actions=[]))
        result = orch.run(week="2026-W21")
        assert result["word_count"] >= 0

    def test_empty_sentiment_summary(self, orch):
        """Empty sentiment summary should not cause division error."""
        orch.db.save_insights(sample_data(
            sentiment_summary={"positive": 0, "negative": 0, "neutral": 0}
        ))
        result = orch.run(week="2026-W21")
        assert isinstance(result, dict)

    def test_zero_reviews_analysed(self, orch):
        orch.db.save_insights(sample_data(total_reviews_analysed=0))
        result = orch.run(week="2026-W21")
        assert result["word_count"] >= 0


# ── Multiple weeks ────────────────────────────────────────────────────────────

class TestMultipleWeeks:

    def test_run_specific_older_week(self, orch, tmp_path):
        """Can generate report for a specific older week."""
        orch.db.save_insights(sample_data("2026-W19"))
        orch.db.save_insights(sample_data("2026-W21"))
        orch.docs.create_document.side_effect = lambda title, content: make_doc_result(tmp_path, "2026-W19")
        result = orch.run(week="2026-W19")
        assert result["week"] == "2026-W19"

    def test_run_latest_picks_most_recent(self, orch, tmp_path):
        """No week arg → picks the most recently generated insights."""
        orch.db.save_insights(sample_data("2026-W19"))
        orch.db.save_insights(sample_data("2026-W21"))
        result = orch.run()
        assert result["week"] == "2026-W21"

    def test_each_week_gets_own_doc_id(self, orch, tmp_path):
        orch.db.save_insights(sample_data("2026-W19"))
        orch.db.save_insights(sample_data("2026-W21"))

        orch.docs.create_document.side_effect = lambda title, content: {
            "doc_id": f"doc-{title[-7:]}",
            "doc_url": f"file://doc-{title[-7:]}",
            "source": "local_file", "title": title,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        orch.run(week="2026-W19")
        orch.run(week="2026-W21")

        w19 = orch.db.get_insights("2026-W19")
        w21 = orch.db.get_insights("2026-W21")
        assert w19["doc_id"] != w21["doc_id"]


# ── _dict_to_insights edge cases ──────────────────────────────────────────────

class TestDictToInsightsEdgeCases:

    def test_missing_sentiment_summary_defaults_to_empty(self, orch):
        data = sample_data()
        del data["sentiment_summary"]
        insights = orch._dict_to_insights(data)
        assert insights.sentiment_summary == {}

    def test_missing_doc_id_defaults_to_none(self, orch):
        data = sample_data()
        del data["doc_id"]
        insights = orch._dict_to_insights(data)
        assert insights.doc_id is None

    def test_missing_email_id_defaults_to_none(self, orch):
        data = sample_data()
        del data["email_id"]
        insights = orch._dict_to_insights(data)
        assert insights.email_id is None

    def test_none_themes_treated_as_empty(self, orch):
        data = sample_data(themes=None)
        insights = orch._dict_to_insights(data)
        assert insights.themes == []

    def test_none_quotes_treated_as_empty(self, orch):
        data = sample_data(quotes=None)
        insights = orch._dict_to_insights(data)
        assert insights.quotes == []

    def test_none_actions_treated_as_empty(self, orch):
        data = sample_data(actions=None)
        insights = orch._dict_to_insights(data)
        assert insights.actions == []

    def test_theme_missing_keywords_defaults_to_empty_list(self, orch):
        data = sample_data(themes=[{
            "name": "T", "description": "D.", "review_count": 1,
            "sentiment": "neutral"
            # no keywords key
        }])
        insights = orch._dict_to_insights(data)
        assert insights.themes[0].keywords == []

    def test_all_sentiment_labels_parsed(self, orch):
        for label in ("positive", "negative", "neutral"):
            data = sample_data(themes=[{
                "name": "T", "description": "D.", "review_count": 1,
                "sentiment": label, "keywords": []
            }])
            insights = orch._dict_to_insights(data)
            assert insights.themes[0].sentiment.value == label


# ── Word count warning ────────────────────────────────────────────────────────

class TestWordCountWarning:

    def test_word_count_reported_in_result(self, orch):
        orch.db.save_insights(sample_data())
        result = orch.run(week="2026-W21")
        assert isinstance(result["word_count"], int)
        assert result["word_count"] > 0

    def test_word_count_within_250_for_standard_insights(self, orch):
        orch.db.save_insights(sample_data())
        result = orch.run(week="2026-W21")
        assert result["word_count"] <= 250


# ── Document creation args ────────────────────────────────────────────────────

class TestDocumentCreationArgs:

    def test_create_document_receives_markdown_content(self, orch):
        """Orchestrator passes markdown (not plain_text) to docs client."""
        orch.db.save_insights(sample_data())
        orch.run(week="2026-W21")
        call_kwargs = orch.docs.create_document.call_args
        content_arg = call_kwargs[1].get("content") or call_kwargs[0][1]
        # Markdown starts with # heading
        assert content_arg.startswith("#")

    def test_create_document_title_contains_week(self, orch):
        orch.db.save_insights(sample_data("2026-W33"))
        orch.docs.create_document.side_effect = lambda title, content: {
            "doc_id": "d", "doc_url": "u", "source": "local_file",
            "title": title, "created_at": datetime.now(timezone.utc).isoformat(),
        }
        orch.run(week="2026-W33")
        call_kwargs = orch.docs.create_document.call_args
        title_arg = call_kwargs[1].get("title") or call_kwargs[0][0]
        assert "2026-W33" in title_arg
