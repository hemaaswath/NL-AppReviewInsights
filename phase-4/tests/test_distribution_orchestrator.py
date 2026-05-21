"""
Tests for DistributionOrchestrator.
"""
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from distribution_orchestrator import DistributionOrchestrator


def workspace_test_path(filename: str) -> Path:
    directory = Path.cwd() / "phase-4" / "test-results" / "unit"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{uuid4().hex}_{filename}"


def sample_insights_data(week="2026-W21"):
    return {
        "week": week,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_reviews_analysed": 73,
        "themes": [
            {
                "name": "App Crashes",
                "description": "Crashes on startup.",
                "review_count": 15,
                "sentiment": "negative",
                "keywords": ["crash"],
            }
        ],
        "quotes": [
            {
                "text": "Crashes every time.",
                "theme_name": "App Crashes",
                "rating": 1,
                "sentiment": "negative",
            }
        ],
        "actions": [
            {
                "description": "Fix crashes.",
                "priority": "high",
                "theme_name": "App Crashes",
                "rationale": "Many affected.",
            }
        ],
        "sentiment_summary": {"positive": 31, "negative": 36, "neutral": 6},
        "doc_id": "doc-abc-123",
        "email_id": None,
    }


@pytest.fixture
def orchestrator():
    orch = DistributionOrchestrator(
        database_path=str(workspace_test_path("test.db")),
        recipient="recipient@example.com",
    )
    orch.gmail = MagicMock()
    orch.gmail.create_draft.return_value = {
        "draft_id": "draft-123",
        "source": "gmail",
        "to": "recipient@example.com",
        "subject": "Subject",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    orch.gmail.send_draft.return_value = {
        "message_id": "msg-123",
        "status": "draft_created",
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    yield orch
    orch.close()


class TestDistributionOrchestratorRun:
    def test_run_returns_draft_created_result(self, orchestrator):
        orchestrator.gmail.send_draft.return_value = {
            "message_id": "msg-123",
            "status": "draft_created",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        orchestrator.db.save_insights(sample_insights_data())
        result = orchestrator.run("2026-W21")

        assert result["status"] == "draft_created"
        assert result["message_id"] == "msg-123"
        assert result["source"] == "gmail"

    def test_run_persists_email_id_after_send(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        orchestrator.run("2026-W21")

        stored = orchestrator.db.get_insights("2026-W21")
        assert stored["email_id"] == "msg-123"

    def test_run_preserves_doc_id_when_saving_email_id(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        orchestrator.run("2026-W21")

        stored = orchestrator.db.get_insights("2026-W21")
        assert stored["doc_id"] == "doc-abc-123"

    def test_run_passes_report_url_to_email(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        orchestrator.run("2026-W21")

        create_args = orchestrator.gmail.create_draft.call_args.kwargs
        assert "https://docs.google.com/document/d/doc-abc-123/edit" in create_args["body"]
        assert "https://docs.google.com/document/d/doc-abc-123/edit" in create_args["html_body"]

    def test_run_raises_if_no_doc_id(self, orchestrator):
        data = sample_insights_data()
        data["doc_id"] = None
        orchestrator.db.save_insights(data)

        with pytest.raises(ValueError, match="No doc_id"):
            orchestrator.run("2026-W21")

    def test_run_raises_if_no_insights(self, orchestrator):
        with pytest.raises(ValueError, match="No insights found"):
            orchestrator.run("9999-W99")

    def test_run_raises_and_does_not_persist_on_draft_only_status(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        orchestrator.gmail.send_draft.return_value = {
            "message_id": None,
            "status": "draft_saved",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

        with pytest.raises(RuntimeError, match="did not create"):
            orchestrator.run("2026-W21")

        stored = orchestrator.db.get_insights("2026-W21")
        assert stored["email_id"] is None

    def test_run_raises_when_local_fallback_draft_saved(self, orchestrator):
        """Local .eml fallback must not be treated as successful Phase 4 (email_id stays null)."""
        orchestrator.db.save_insights(sample_insights_data())
        orchestrator.gmail.create_draft.return_value = {
            "draft_id": "local://phase-4/test-results/drafts/test.eml",
            "source": "local_file",
            "to": "recipient@example.com",
            "subject": "Subject",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        orchestrator.gmail.send_draft.return_value = {
            "message_id": None,
            "status": "draft_saved",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

        with pytest.raises(RuntimeError, match="did not create"):
            orchestrator.run("2026-W21")

        assert orchestrator.db.get_insights("2026-W21")["email_id"] is None

    def test_run_does_not_persist_when_send_raises(self, orchestrator):
        orchestrator.db.save_insights(sample_insights_data())
        orchestrator.gmail.send_draft.side_effect = RuntimeError("send failed")

        with pytest.raises(RuntimeError, match="send failed"):
            orchestrator.run("2026-W21")

        stored = orchestrator.db.get_insights("2026-W21")
        assert stored["email_id"] is None

    def test_run_uses_latest_week_when_not_specified(self, orchestrator):
        older = sample_insights_data("2026-W20")
        newer = sample_insights_data("2026-W21")
        older["generated_at"] = datetime(2026, 5, 10, tzinfo=timezone.utc).isoformat()
        newer["generated_at"] = datetime(2026, 5, 17, tzinfo=timezone.utc).isoformat()
        orchestrator.db.save_insights(older)
        orchestrator.db.save_insights(newer)

        result = orchestrator.run()

        assert result["week"] == "2026-W21"

    def test_invalid_recipient_raises(self):
        orch = DistributionOrchestrator(
            database_path=str(workspace_test_path("test.db")),
            recipient="invalid",
        )
        try:
            with pytest.raises(ValueError, match="Invalid or missing recipient"):
                orch.run("2026-W21")
        finally:
            orch.close()


class TestResolveDocUrl:
    def test_resolve_google_doc_id(self, orchestrator):
        url = orchestrator._resolve_doc_url({"doc_id": "doc-abc-123"})
        assert url == "https://docs.google.com/document/d/doc-abc-123/edit"

    def test_resolve_https_url(self, orchestrator):
        url = "https://docs.google.com/document/d/doc-abc-123/edit"
        assert orchestrator._resolve_doc_url({"doc_id": url}) == url

    def test_resolve_http_url(self, orchestrator):
        url = "http://localhost/report"
        assert orchestrator._resolve_doc_url({"doc_id": url}) == url

    def test_resolve_file_uri(self, orchestrator):
        url = "file://C:/tmp/report.md"
        assert orchestrator._resolve_doc_url({"doc_id": url}) == url

    def test_resolve_local_path(self, orchestrator):
        path = workspace_test_path("report.md")
        path.write_text("report", encoding="utf-8")

        url = orchestrator._resolve_doc_url({"doc_id": str(path)})

        assert url.startswith("file://")
        assert str(path.resolve()) in url
