"""
ReportOrchestrator — Phase 3 entry point.

Loads WeeklyInsights from the database, formats the report,
creates a Google Docs document (or local file fallback),
and stores the doc_id back in the insights record.
"""
import os
import json
from typing import Optional
from dotenv import load_dotenv

from shared.database import DatabaseManager
from shared.models import WeeklyInsights, Theme, Quote, ActionItem, SentimentLabel

from report_formatter import ReportFormatter
from google_docs_client import GoogleDocsClient

load_dotenv()


class ReportOrchestrator:
    """Orchestrates Phase 3: format insights → create Google Doc."""

    def __init__(
        self,
        database_path: Optional[str] = None,
        mcp_server_url: Optional[str] = None,
    ):
        self.database_path = database_path or os.getenv("DATABASE_PATH", "data/reviews.db")
        self.db        = DatabaseManager(self.database_path)
        self.formatter = ReportFormatter()
        self.docs      = GoogleDocsClient(mcp_server_url=mcp_server_url)

    def run(self, week: Optional[str] = None) -> dict:
        """Run the full Phase 3 pipeline for a given week.

        Args:
            week: ISO week string (e.g. '2026-W21'). Defaults to latest.

        Returns:
            dict with keys: week, doc_id, doc_url, source, word_count, report
        """
        print(f"\n{'='*60}")
        print("Phase 3 — Report Generation")
        print(f"{'='*60}")

        # ── 1. Load insights ──────────────────────────────────────────────────
        insights_data = self.db.get_insights(week)
        if not insights_data:
            raise ValueError(
                f"No insights found for week '{week or 'latest'}'. "
                "Run Phase 2 first."
            )

        insights = self._dict_to_insights(insights_data)
        print(f"Loaded insights for week: {insights.week}")
        print(f"  Reviews analysed : {insights.total_reviews_analysed}")
        print(f"  Themes           : {len(insights.themes)}")
        print(f"  Quotes           : {len(insights.quotes)}")
        print(f"  Actions          : {len(insights.actions)}")

        # ── 2. Format report ──────────────────────────────────────────────────
        print("\n[1/3] Formatting report...")
        report = self.formatter.format(insights)
        print(f"  Word count : {report['word_count']} / {self.formatter.MAX_WORDS} max")

        if report["word_count"] > self.formatter.MAX_WORDS:
            print(f"  WARNING: Report exceeds {self.formatter.MAX_WORDS} words — "
                  f"consider trimming themes or quotes")

        # ── 3. Create document ────────────────────────────────────────────────
        print("\n[2/3] Creating document...")
        doc_result = self.docs.create_document(
            title=report["title"],
            content=report["markdown"],   # use markdown for richer local output
        )
        print(f"  Source   : {doc_result['source']}")
        print(f"  Doc ID   : {doc_result['doc_id']}")
        print(f"  Doc URL  : {doc_result['doc_url']}")

        # ── 4. Persist doc_id back to insights ────────────────────────────────
        print("\n[3/3] Saving doc_id to database...")
        insights_data["doc_id"] = doc_result["doc_id"]
        self.db.save_insights(insights_data)
        print(f"  doc_id saved for week {insights.week}")

        print(f"\n{'='*60}")
        print("REPORT GENERATION COMPLETE")
        print(f"{'='*60}\n")

        return {
            "week":       insights.week,
            "doc_id":     doc_result["doc_id"],
            "doc_url":    doc_result["doc_url"],
            "source":     doc_result["source"],
            "word_count": report["word_count"],
            "report":     report,
        }

    def _dict_to_insights(self, data: dict) -> WeeklyInsights:
        """Reconstruct a WeeklyInsights Pydantic model from a DB dict."""
        themes = [
            Theme(
                name=t["name"],
                description=t["description"],
                review_count=t["review_count"],
                sentiment=SentimentLabel(t["sentiment"]),
                keywords=t.get("keywords", []),
            )
            for t in (data.get("themes") or [])
        ]
        quotes = [
            Quote(
                text=q["text"],
                theme_name=q["theme_name"],
                rating=q["rating"],
                sentiment=SentimentLabel(q["sentiment"]),
            )
            for q in (data.get("quotes") or [])
        ]
        actions = [
            ActionItem(
                description=a["description"],
                priority=a["priority"],
                theme_name=a["theme_name"],
                rationale=a["rationale"],
            )
            for a in (data.get("actions") or [])
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
    """Entry point for Phase 3."""
    orch = ReportOrchestrator()
    result = orch.run()
    print(f"Report URL: {result['doc_url']}")
    print(f"Word count: {result['word_count']}")
    orch.close()
    return result


if __name__ == "__main__":
    main()
