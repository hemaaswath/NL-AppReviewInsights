"""
Tests for ReportFormatter.
"""
import pytest
from datetime import datetime, timezone
from shared.models import (
    WeeklyInsights, Theme, Quote, ActionItem, SentimentLabel
)
from report_formatter import ReportFormatter


def make_insights(
    week="2026-W21",
    total=73,
    themes=None,
    quotes=None,
    actions=None,
    sentiment=None,
):
    return WeeklyInsights(
        week=week,
        generated_at=datetime(2026, 5, 18, 18, 0, 0, tzinfo=timezone.utc),
        total_reviews_analysed=total,
        themes=themes or [
            Theme(name="App Crashes", description="Crashes on startup.",
                  review_count=15, sentiment=SentimentLabel.NEGATIVE,
                  keywords=["crash", "bug"]),
            Theme(name="Good UI", description="Clean interface.",
                  review_count=20, sentiment=SentimentLabel.POSITIVE,
                  keywords=["ui", "design"]),
        ],
        quotes=quotes or [
            Quote(text="App crashes every time.", theme_name="App Crashes",
                  rating=1, sentiment=SentimentLabel.NEGATIVE),
            Quote(text="Love the clean interface!", theme_name="Good UI",
                  rating=5, sentiment=SentimentLabel.POSITIVE),
            Quote(text="Works okay but slow.", theme_name="App Crashes",
                  rating=3, sentiment=SentimentLabel.NEUTRAL),
        ],
        actions=actions or [
            ActionItem(description="Fix crash on portfolio screen.",
                       priority="high", theme_name="App Crashes",
                       rationale="Many users affected."),
            ActionItem(description="Optimise load times.",
                       priority="medium", theme_name="Performance",
                       rationale="Slow on older devices."),
            ActionItem(description="Add dark mode.",
                       priority="low", theme_name="UI",
                       rationale="Frequently requested."),
        ],
        sentiment_summary=sentiment or {"positive": 31, "negative": 36, "neutral": 6},
    )


@pytest.fixture
def formatter():
    return ReportFormatter()


@pytest.fixture
def insights():
    return make_insights()


class TestReportFormatterOutput:

    def test_format_returns_dict(self, formatter, insights):
        result = formatter.format(insights)
        assert isinstance(result, dict)

    def test_format_has_required_keys(self, formatter, insights):
        result = formatter.format(insights)
        for key in ("title", "plain_text", "markdown", "word_count", "sections"):
            assert key in result

    def test_title_contains_week(self, formatter, insights):
        result = formatter.format(insights)
        assert "2026-W21" in result["title"]

    def test_title_contains_groww(self, formatter, insights):
        result = formatter.format(insights)
        assert "Groww" in result["title"]

    def test_word_count_within_limit(self, formatter, insights):
        result = formatter.format(insights)
        assert result["word_count"] <= formatter.MAX_WORDS, (
            f"Word count {result['word_count']} exceeds {formatter.MAX_WORDS}"
        )

    def test_word_count_matches_plain_text(self, formatter, insights):
        result = formatter.format(insights)
        assert result["word_count"] == len(result["plain_text"].split())

    def test_plain_text_is_string(self, formatter, insights):
        result = formatter.format(insights)
        assert isinstance(result["plain_text"], str)
        assert len(result["plain_text"]) > 0

    def test_markdown_is_string(self, formatter, insights):
        result = formatter.format(insights)
        assert isinstance(result["markdown"], str)
        assert len(result["markdown"]) > 0


class TestReportSections:

    def test_all_sections_present(self, formatter, insights):
        result = formatter.format(insights)
        sections = result["sections"]
        for key in ("header", "sentiment", "themes", "quotes", "actions", "footer"):
            assert key in sections

    def test_header_contains_week(self, formatter, insights):
        result = formatter.format(insights)
        assert "2026-W21" in result["sections"]["header"]

    def test_header_contains_review_count(self, formatter, insights):
        result = formatter.format(insights)
        assert "73" in result["sections"]["header"]

    def test_sentiment_section_has_all_three_labels(self, formatter, insights):
        result = formatter.format(insights)
        s = result["sections"]["sentiment"]
        assert "Positive" in s
        assert "Negative" in s
        assert "Neutral" in s

    def test_sentiment_percentages_present(self, formatter, insights):
        result = formatter.format(insights)
        s = result["sections"]["sentiment"]
        assert "%" in s

    def test_themes_section_lists_all_themes(self, formatter, insights):
        result = formatter.format(insights)
        t = result["sections"]["themes"]
        assert "App Crashes" in t
        assert "Good UI" in t

    def test_themes_section_has_review_counts(self, formatter, insights):
        result = formatter.format(insights)
        t = result["sections"]["themes"]
        assert "15" in t   # App Crashes count
        assert "20" in t   # Good UI count

    def test_quotes_section_has_all_quotes(self, formatter, insights):
        result = formatter.format(insights)
        q = result["sections"]["quotes"]
        assert "App crashes every time" in q
        assert "Love the clean interface" in q

    def test_quotes_section_has_ratings(self, formatter, insights):
        result = formatter.format(insights)
        q = result["sections"]["quotes"]
        assert "1★" in q
        assert "5★" in q

    def test_actions_section_has_all_actions(self, formatter, insights):
        result = formatter.format(insights)
        a = result["sections"]["actions"]
        assert "Fix crash" in a
        assert "Optimise load" in a
        assert "dark mode" in a

    def test_actions_section_has_priorities(self, formatter, insights):
        result = formatter.format(insights)
        a = result["sections"]["actions"]
        assert "HIGH" in a
        assert "MEDIUM" in a
        assert "LOW" in a

    def test_footer_has_generated_date(self, formatter, insights):
        result = formatter.format(insights)
        assert "2026-05-18" in result["sections"]["footer"]


class TestReportMarkdown:

    def test_markdown_has_h1_title(self, formatter, insights):
        result = formatter.format(insights)
        assert result["markdown"].startswith("# ")

    def test_markdown_has_sentiment_table(self, formatter, insights):
        result = formatter.format(insights)
        assert "|" in result["markdown"]
        assert "Positive" in result["markdown"]

    def test_markdown_has_theme_headings(self, formatter, insights):
        result = formatter.format(insights)
        assert "## " in result["markdown"]

    def test_markdown_has_blockquotes(self, formatter, insights):
        result = formatter.format(insights)
        assert "> " in result["markdown"]

    def test_markdown_has_action_bullets(self, formatter, insights):
        result = formatter.format(insights)
        assert "- " in result["markdown"]


class TestReportEdgeCases:

    def test_empty_themes_does_not_crash(self, formatter):
        insights = make_insights(themes=[], quotes=[], actions=[])
        result = formatter.format(insights)
        assert result["word_count"] >= 0

    def test_long_quote_truncated(self, formatter):
        long_quote = "x" * 200
        insights = make_insights(quotes=[
            Quote(text=long_quote, theme_name="Test", rating=3,
                  sentiment=SentimentLabel.NEUTRAL),
            Quote(text="Short quote.", theme_name="Test", rating=4,
                  sentiment=SentimentLabel.POSITIVE),
            Quote(text="Another quote.", theme_name="Test", rating=2,
                  sentiment=SentimentLabel.NEGATIVE),
        ])
        result = formatter.format(insights)
        # Long quote should be truncated in output
        assert long_quote not in result["plain_text"]
        assert "..." in result["plain_text"]

    def test_word_count_helper(self, formatter):
        assert formatter.word_count("hello world") == 2
        assert formatter.word_count("") == 0
        assert formatter.word_count("one") == 1

    def test_different_weeks_produce_different_titles(self, formatter):
        r1 = formatter.format(make_insights(week="2026-W20"))
        r2 = formatter.format(make_insights(week="2026-W21"))
        assert r1["title"] != r2["title"]

    def test_zero_sentiment_counts_no_division_error(self, formatter):
        insights = make_insights(sentiment={"positive": 0, "negative": 0, "neutral": 0})
        result = formatter.format(insights)
        assert result["word_count"] >= 0
