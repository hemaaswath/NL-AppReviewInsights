"""
Tests for EmailComposer.
"""
import pytest

from email_composer import EmailComposer, validate_email
from shared.models import ActionItem, Quote, SentimentLabel, Theme, WeeklyInsights


def sample_insights() -> WeeklyInsights:
    return WeeklyInsights(
        week="2026-W21",
        total_reviews_analysed=73,
        themes=[
            Theme(
                name="Crash <script>",
                description="Crashes on startup.",
                review_count=15,
                sentiment=SentimentLabel.NEGATIVE,
                keywords=["crash"],
            )
        ],
        quotes=[
            Quote(
                text="Crashes every time.",
                theme_name="Crash",
                rating=1,
                sentiment=SentimentLabel.NEGATIVE,
            )
        ],
        actions=[
            ActionItem(
                description="Fix <startup> crashes.",
                priority="high",
                theme_name="Crash",
                rationale="Many affected.",
            )
        ],
        sentiment_summary={"positive": 31, "negative": 36, "neutral": 6},
        doc_id="doc-123",
    )


def empty_insights() -> WeeklyInsights:
    return WeeklyInsights(
        week="2026-W22",
        total_reviews_analysed=0,
        themes=[],
        quotes=[],
        actions=[],
        sentiment_summary={},
        doc_id="doc-empty",
    )


class TestValidateEmail:
    def test_accepts_valid_email(self):
        assert validate_email("recipient@example.com") is True

    def test_accepts_plus_address(self):
        assert validate_email("product+reviews@example.co.in") is True

    def test_rejects_invalid_email(self):
        assert validate_email("not-an-email") is False

    def test_rejects_multiple_recipients(self):
        assert validate_email("a@example.com,b@example.com") is False


class TestEmailComposer:
    def test_compose_has_required_keys(self):
        email = EmailComposer().compose(
            sample_insights(),
            "https://docs.google.com/document/d/doc-123/edit",
            "recipient@example.com",
        )
        for key in ("to", "subject", "body", "html_body", "week", "doc_url"):
            assert key in email

    def test_subject_identifies_report_and_week(self):
        email = EmailComposer().compose(sample_insights(), "https://example.com/doc", "a@b.com")
        assert "Weekly Review Pulse" in email["subject"]
        assert "2026-W21" in email["subject"]

    def test_body_contains_clickable_doc_link(self):
        url = "https://docs.google.com/document/d/doc-123/edit"
        email = EmailComposer().compose(sample_insights(), url, "a@b.com")
        assert url in email["body"]
        assert f'href="{url}"' in email["html_body"]

    def test_recipient_is_trimmed(self):
        email = EmailComposer().compose(sample_insights(), "https://example.com/doc", "  a@b.com  ")
        assert email["to"] == "a@b.com"

    def test_html_escapes_insight_content(self):
        email = EmailComposer().compose(sample_insights(), "https://example.com/doc", "a@b.com")
        assert "Crash &lt;script&gt;" in email["html_body"]
        assert "Fix &lt;startup&gt; crashes." in email["html_body"]
        assert "<script>" not in email["html_body"]

    def test_invalid_recipient_raises(self):
        with pytest.raises(ValueError, match="Invalid recipient"):
            EmailComposer().compose(sample_insights(), "https://example.com/doc", "bad")

    def test_missing_doc_url_raises(self):
        with pytest.raises(ValueError, match="doc_url is required"):
            EmailComposer().compose(sample_insights(), "", "a@b.com")

    def test_empty_insights_render_without_crashing(self):
        email = EmailComposer().compose(empty_insights(), "https://example.com/doc", "a@b.com")

        assert "No themes available" in email["html_body"]
        assert "No action items available" in email["html_body"]
        assert "Reviews analysed: 0" in email["body"]

    def test_doc_url_is_escaped_in_html_attributes(self):
        url = 'https://example.com/doc?x=1&next="bad"'
        email = EmailComposer().compose(sample_insights(), url, "a@b.com")

        assert 'href="https://example.com/doc?x=1&amp;next=&quot;bad&quot;"' in email["html_body"]
