"""
EmailComposer - builds the Phase 4 weekly pulse email.

The email includes a clear subject, a concise plain-text body, an HTML body
with the report link, and only aggregate insights rather than raw review text.
"""
import html
import re

from shared.models import WeeklyInsights

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def validate_email(address: str) -> bool:
    """Return True if address looks like a valid single email address."""
    return bool(_EMAIL_RE.match(address.strip())) if address else False


class EmailComposer:
    """Composes the weekly pulse email from WeeklyInsights and a report URL."""

    def compose(self, insights: WeeklyInsights, doc_url: str, recipient: str) -> dict:
        """Build the subject, plain body, HTML body, and metadata."""
        if not validate_email(recipient):
            raise ValueError(f"Invalid recipient email address: '{recipient}'")
        if not doc_url:
            raise ValueError("doc_url is required")

        subject = self._subject(insights)
        body = self._plain_body(insights, doc_url)
        html_body = self._html_body(insights, doc_url)

        return {
            "to": recipient.strip(),
            "subject": subject,
            "body": body,
            "html_body": html_body,
            "week": insights.week,
            "doc_url": doc_url,
        }

    def _subject(self, insights: WeeklyInsights) -> str:
        return f"Groww App - Weekly Review Pulse - {insights.week}"

    def _plain_body(self, insights: WeeklyInsights, doc_url: str) -> str:
        sentiment = insights.sentiment_summary
        positive = sentiment.get("positive", 0)
        negative = sentiment.get("negative", 0)
        total = insights.total_reviews_analysed or 1
        negative_pct = round(negative / total * 100)

        top_theme = insights.themes[0].name if insights.themes else "N/A"
        top_action = insights.actions[0].description if insights.actions else "N/A"
        top_priority = insights.actions[0].priority.upper() if insights.actions else "N/A"

        return "\n".join(
            [
                "Hi,",
                "",
                f"This week's Groww app review insights are ready for {insights.week}.",
                "",
                "Highlights",
                f"- Reviews analysed: {insights.total_reviews_analysed}",
                f"- Sentiment: {positive} positive / {negative} negative ({negative_pct}% negative)",
                f"- Top theme: {top_theme}",
                f"- Top action: [{top_priority}] {top_action}",
                "",
                "View full report:",
                doc_url,
                "",
                "The report includes top themes, representative user quotes, and three prioritised action items for the product team.",
                "",
                "Groww Review Insights Analyzer",
                f"Week {insights.week}",
            ]
        )

    def _html_body(self, insights: WeeklyInsights, doc_url: str) -> str:
        sentiment = insights.sentiment_summary
        positive = sentiment.get("positive", 0)
        negative = sentiment.get("negative", 0)
        neutral = sentiment.get("neutral", 0)
        total = insights.total_reviews_analysed or 1
        positive_pct = round(positive / total * 100)
        negative_pct = round(negative / total * 100)

        safe_week = html.escape(insights.week)
        safe_url = html.escape(doc_url, quote=True)

        theme_rows = "".join(
            "<tr>"
            f"<td>{index}.</td>"
            f"<td><b>{html.escape(theme.name)}</b></td>"
            f"<td>{theme.review_count} reviews</td>"
            f"<td>{html.escape(theme.sentiment.value)}</td>"
            "</tr>"
            for index, theme in enumerate(insights.themes, 1)
        )
        if not theme_rows:
            theme_rows = '<tr><td colspan="4">No themes available</td></tr>'

        action_rows = "".join(
            "<tr>"
            f"<td><b>[{html.escape(action.priority.upper())}]</b></td>"
            f"<td>{html.escape(action.description)}</td>"
            "</tr>"
            for action in insights.actions
        )
        if not action_rows:
            action_rows = '<tr><td colspan="2">No action items available</td></tr>'

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
<h2 style="color: #1a73e8;">Groww App - Weekly Review Pulse - {safe_week}</h2>

<p>Hi,</p>
<p>This week's Groww app review insights are ready. Here's a quick summary:</p>

<h3>Sentiment Overview</h3>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
  <tr style="background:#f5f5f5;">
    <th>Positive</th><th>Negative</th><th>Neutral</th><th>Total</th>
  </tr>
  <tr>
    <td>{positive} ({positive_pct}%)</td>
    <td>{negative} ({negative_pct}%)</td>
    <td>{neutral}</td>
    <td>{insights.total_reviews_analysed}</td>
  </tr>
</table>

<h3>Top Themes</h3>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
  <tr style="background:#f5f5f5;">
    <th>#</th><th>Theme</th><th>Volume</th><th>Sentiment</th>
  </tr>
  {theme_rows}
</table>

<h3>Action Items</h3>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
  <tr style="background:#f5f5f5;"><th>Priority</th><th>Action</th></tr>
  {action_rows}
</table>

<h3>Full Report</h3>
<p>
  <a href="{safe_url}" style="background:#1a73e8;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;display:inline-block;">
    View Weekly Pulse Report
  </a>
</p>
<p style="font-size:12px;">Or copy this link: {safe_url}</p>

<hr>
<p style="font-size:11px;color:#888;">Groww Review Insights Analyzer | Week {safe_week}</p>
</body>
</html>"""
