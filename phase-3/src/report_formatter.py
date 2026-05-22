"""
ReportFormatter — converts WeeklyInsights into a structured one-page
weekly pulse report (≤250 words, scannable format).

Produces two representations:
  - plain_text : for Google Docs insertion
  - markdown   : for local file output / preview
"""
from typing import Any, Optional

from shared.models import WeeklyInsights

PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
SENTIMENT_ICON = {"positive": "😊", "negative": "😞", "neutral": "😐"}


class ReportFormatter:
    """Formats WeeklyInsights into a concise weekly pulse report."""

    MAX_WORDS = 250

    def format(
        self,
        insights: WeeklyInsights,
        week_over_week: Optional[dict[str, Any]] = None,
    ) -> dict:
        """Format insights into plain text and markdown representations.

        Args:
            insights: WeeklyInsights object from Phase 2.
            week_over_week: Optional WoW dict from shared.week_over_week.

        Returns:
            dict with keys:
              - title        : document title string
              - plain_text   : full report as plain text (for Docs insertion)
              - markdown     : full report as markdown (for local preview)
              - word_count   : actual word count of plain_text
              - sections     : dict of individual section strings
        """
        title = f"Weekly Pulse — Groww App Reviews — {insights.week}"

        sections = {
            "header":   self._header(insights),
            "sentiment": self._sentiment_section(insights),
            "themes":   self._themes_section(insights),
            "quotes":   self._quotes_section(insights),
            "actions":  self._actions_section(insights),
            "footer":   self._footer(insights),
        }
        if week_over_week:
            sections["wow"] = self._wow_section(week_over_week)

        plain_text = "\n\n".join(sections.values())
        markdown   = self._to_markdown(title, insights, sections)
        word_count = len(plain_text.split())

        return {
            "title":      title,
            "plain_text": plain_text,
            "markdown":   markdown,
            "word_count": word_count,
            "sections":   sections,
        }

    # ── Section builders ──────────────────────────────────────────────────────

    def _header(self, insights: WeeklyInsights) -> str:
        return (
            f"WEEKLY PULSE — GROWW APP REVIEWS\n"
            f"Week: {insights.week}  |  Reviews analysed: {insights.total_reviews_analysed}"
        )

    def _sentiment_section(self, insights: WeeklyInsights) -> str:
        s = insights.sentiment_summary
        pos = s.get("positive", 0)
        neg = s.get("negative", 0)
        neu = s.get("neutral", 0)
        total = pos + neg + neu or 1
        pos_pct = round(pos / total * 100)
        neg_pct = round(neg / total * 100)
        return (
            f"SENTIMENT OVERVIEW\n"
            f"Positive: {pos} ({pos_pct}%)  |  "
            f"Negative: {neg} ({neg_pct}%)  |  "
            f"Neutral: {neu}"
        )

    def _wow_section(self, wow: dict[str, Any]) -> str:
        lines = ["WEEK OVER WEEK"]
        lines.append(wow.get("headline", ""))
        for t in (wow.get("rising_themes") or [])[:2]:
            lines.append(f"  ↑ {t['name']}: +{t['delta']} mentions vs prior week")
        return "\n".join(lines)

    def _themes_section(self, insights: WeeklyInsights) -> str:
        lines = ["PRODUCT AREAS (GROWW MAP)"]
        for i, theme in enumerate(insights.themes, 1):
            icon = SENTIMENT_ICON.get(theme.sentiment.value, "")
            # Keep it tight: name + sentiment icon + review count only
            lines.append(
                f"{i}. {theme.name} {icon} ({theme.review_count} reviews)"
            )
        return "\n".join(lines)

    def _quotes_section(self, insights: WeeklyInsights) -> str:
        lines = ["USER VOICES"]
        for quote in insights.quotes:
            # Truncate very long quotes to keep word count under control
            text = quote.text if len(quote.text) <= 120 else quote.text[:117] + "..."
            lines.append(f'"{text}" — {quote.rating}★ ({quote.theme_name})')
        return "\n".join(lines)

    def _actions_section(self, insights: WeeklyInsights) -> str:
        lines = ["ACTION IDEAS"]
        for action in insights.actions:
            icon = PRIORITY_ICON.get(action.priority, "▶")
            # Keep description only (rationale goes in markdown, not plain text)
            lines.append(
                f"{icon} [{action.priority.upper()}] {action.description}"
            )
        return "\n".join(lines)

    def _footer(self, insights: WeeklyInsights) -> str:
        from datetime import datetime, timezone
        generated = insights.generated_at.strftime("%Y-%m-%d %H:%M UTC") \
            if insights.generated_at else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return f"Generated: {generated}  |  Powered by Groww Review Insights Analyzer"

    # ── Markdown renderer ─────────────────────────────────────────────────────

    def _to_markdown(self, title: str, insights: WeeklyInsights, sections: dict) -> str:
        s = insights.sentiment_summary
        pos, neg, neu = s.get("positive", 0), s.get("negative", 0), s.get("neutral", 0)
        total = pos + neg + neu or 1

        lines = [
            f"# {title}",
            "",
            f"> **{insights.total_reviews_analysed} reviews analysed** | "
            f"Week {insights.week}",
            "",
            "---",
            "",
            "## 📊 Sentiment Overview",
            "",
            f"| Positive | Negative | Neutral |",
            f"|----------|----------|---------|",
            f"| {pos} ({round(pos/total*100)}%) | {neg} ({round(neg/total*100)}%) | {neu} |",
            "",
            "## 🏷️ Top Themes",
            "",
        ]

        for i, theme in enumerate(insights.themes, 1):
            icon = SENTIMENT_ICON.get(theme.sentiment.value, "")
            lines.append(
                f"{i}. **{theme.name}** {icon} — {theme.description} "
                f"*({theme.review_count} reviews)*"
            )

        lines += ["", "## 💬 User Voices", ""]
        for quote in insights.quotes:
            text = quote.text if len(quote.text) <= 120 else quote.text[:117] + "..."
            lines.append(f'> "{text}"')
            lines.append(f'> — {quote.rating}★ · *{quote.theme_name}*')
            lines.append("")

        lines += ["## ⚡ Action Ideas", ""]
        for action in insights.actions:
            icon = PRIORITY_ICON.get(action.priority, "▶")
            lines.append(f"- {icon} **[{action.priority.upper()}]** {action.description}")
            lines.append(f"  *{action.rationale}*")
            lines.append("")

        lines += [
            "---",
            "",
            f"*{sections['footer']}*",
        ]

        return "\n".join(lines)

    def word_count(self, text: str) -> int:
        """Count words in a text string."""
        return len(text.split())
