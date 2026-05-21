"""
DistributionOrchestrator - Phase 4 entry point.

Loads WeeklyInsights plus doc_id from the database, composes the email, creates
and sends a Gmail draft through MCP, and stores the sent message ID back in the
insights record.
"""
import os
from typing import Optional

from dotenv import load_dotenv

from shared.database import DatabaseManager
from shared.models import ActionItem, Quote, SentimentLabel, Theme, WeeklyInsights

from email_composer import EmailComposer, validate_email
from gmail_client import GmailMCPClient
from agent_debug import agent_log

load_dotenv()


class DistributionOrchestrator:
    """Orchestrates Phase 4: compose email, create Gmail draft, send it."""

    def __init__(
        self,
        database_path: Optional[str] = None,
        mcp_server_url: Optional[str] = None,
        recipient: Optional[str] = None,
        allow_local_fallback: bool = False,
    ):
        self.database_path = database_path or os.getenv("DATABASE_PATH", "data/reviews.db")
        self.recipient = recipient or os.getenv("EMAIL_RECIPIENT", "")
        self.db = DatabaseManager(self.database_path)
        self.composer = EmailComposer()
        self.gmail = GmailMCPClient(
            mcp_server_url=mcp_server_url,
            allow_local_fallback=allow_local_fallback,
        )

    def run(self, week: Optional[str] = None) -> dict:
        """Run the full Phase 4 pipeline for a given week."""
        print(f"\n{'=' * 60}")
        print("Phase 4 - Distribution")
        print(f"{'=' * 60}")

        if not validate_email(self.recipient):
            raise ValueError(
                f"Invalid or missing recipient email: '{self.recipient}'. "
                "Set EMAIL_RECIPIENT in .env."
            )
        print(f"Recipient: {self.recipient}")

        insights_data = self.db.get_insights(week)
        if not insights_data:
            raise ValueError(
                f"No insights found for week '{week or 'latest'}'. Run Phase 2 first."
            )

        insights = self._dict_to_insights(insights_data)
        doc_url = self._resolve_doc_url(insights_data)
        print(f"Week     : {insights.week}")
        print(f"Doc URL  : {doc_url}")

        print("\n[1/4] Composing email...")
        email = self.composer.compose(
            insights=insights,
            doc_url=doc_url,
            recipient=self.recipient,
        )
        print(f"  Subject : {email['subject']}")

        agent_log(
            "distribution_orchestrator.py:run",
            "before_create_draft",
            {
                "week": insights.week,
                "doc_url_scheme": doc_url.split(":", 1)[0] if doc_url else "",
                "allow_local_fallback": self.gmail.allow_local_fallback,
            },
            hypothesis_id="H4",
        )

        print("\n[2/4] Creating Gmail draft...")
        draft = self.gmail.create_draft(
            to=email["to"],
            subject=email["subject"],
            body=email["body"],
            html_body=email["html_body"],
        )
        print(f"  Source   : {draft['source']}")
        print(f"  Draft ID : {draft['draft_id']}")

        print("\n[3/4] Confirming Gmail draft (saksham-mcp-server creates drafts only)...")
        send_result = self.gmail.send_draft(draft["draft_id"])
        print(f"  Status     : {send_result['status']}")
        print(f"  Draft ID   : {send_result['message_id']}")

        agent_log(
            "distribution_orchestrator.py:run",
            "after_send_draft",
            {
                "draft_source": draft.get("source"),
                "send_status": send_result.get("status"),
                "has_message_id": bool(send_result.get("message_id")),
            },
            hypothesis_id="H4,H5",
        )

        if send_result["status"] not in ("sent", "draft_created") or not send_result["message_id"]:
            raise RuntimeError(
                "Phase 4 did not create a Gmail draft via MCP. "
                f"Status was '{send_result['status']}'."
            )

        print("\n[4/4] Saving draft id to database (email_id)...")
        insights_data["email_id"] = send_result["message_id"]
        self.db.save_insights(insights_data)
        print(f"  email_id saved for week {insights.week}")

        print(f"\n{'=' * 60}")
        print("DISTRIBUTION COMPLETE")
        print(f"{'=' * 60}\n")

        return {
            "week": insights.week,
            "draft_id": draft["draft_id"],
            "message_id": send_result["message_id"],
            "status": send_result["status"],
            "recipient": self.recipient,
            "subject": email["subject"],
            "doc_url": doc_url,
            "source": draft["source"],
        }

    def _resolve_doc_url(self, insights_data: dict) -> str:
        """Resolve Phase 3 doc_id into a usable report URL."""
        doc_id = insights_data.get("doc_id")
        if not doc_id:
            raise ValueError("No doc_id found in insights. Run Phase 3 first to generate the report.")
        if doc_id.startswith("file://") or doc_id.startswith("http://") or doc_id.startswith("https://"):
            return doc_id
        if os.path.exists(doc_id):
            return f"file://{os.path.abspath(doc_id)}"
        return f"https://docs.google.com/document/d/{doc_id}/edit"

    def _dict_to_insights(self, data: dict) -> WeeklyInsights:
        """Reconstruct WeeklyInsights Pydantic model from a DB dict."""
        themes = [
            Theme(
                name=theme["name"],
                description=theme["description"],
                review_count=theme["review_count"],
                sentiment=SentimentLabel(theme["sentiment"]),
                keywords=theme.get("keywords", []),
            )
            for theme in (data.get("themes") or [])
        ]
        quotes = [
            Quote(
                text=quote["text"],
                theme_name=quote["theme_name"],
                rating=quote["rating"],
                sentiment=SentimentLabel(quote["sentiment"]),
            )
            for quote in (data.get("quotes") or [])
        ]
        actions = [
            ActionItem(
                description=action["description"],
                priority=action["priority"],
                theme_name=action["theme_name"],
                rationale=action["rationale"],
            )
            for action in (data.get("actions") or [])
        ]
        return WeeklyInsights(
            week=data["week"],
            total_reviews_analysed=data["total_reviews_analysed"],
            themes=themes,
            quotes=quotes,
            actions=actions,
            sentiment_summary=data.get("sentiment_summary", {}),
            doc_id=data.get("doc_id"),
            email_id=data.get("email_id"),
        )

    def close(self):
        self.db.close()


def main():
    """Entry point for Phase 4."""
    orchestrator = DistributionOrchestrator()
    try:
        result = orchestrator.run()
        print(f"Status     : {result['status']}")
        print(f"Recipient  : {result['recipient']}")
        print(f"Message ID : {result['message_id']}")
        return result
    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
