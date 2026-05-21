"""
Extended corner-case tests for ReportFormatter.
"""
import pytest
from datetime import datetime, timezone
from shared.models import (
    WeeklyInsights, Theme, Quote, ActionItem, SentimentLabel
)
from report_formatter import ReportFormatter, PRIORITY_ICON, SENTIMENT_ICON


def make_insights(**kwargs):
    defaults = dict(
        week="2026-W21",
        generated_at=datetime(2026, 5, 18, 18, 0, 0, tzinfo=timezone.utc),
        total_reviews_analysed=10,
        themes=[
            Theme(name="Crashes", description="App crashes.", review_count=5,
                  sentiment=SentimentLabel.NEGATIVE, keywords=["crash"]),
        ],
        quotes=[
            Quote(text="It crashes.", theme_name="Crashes", rating=1,
                  sentiment=SentimentLabel.NEGATIVE),
            Quote(text="Okay app.", theme_name="Crashes", rating=3,
                  sentiment=SentimentLabel.NEUTRAL),
            Quote(text="Love it!", theme_name="Crashes", rating=5,
                  sentiment=SentimentLabel.POSITIVE),
        ],
        actions=[
            ActionItem(description="Fix crashes.", priority="high",
                       theme_name="Crashes", rationale="Many affected."),
            ActionItem(description="Improve speed.", priority="medium",
                       theme_name="Speed", rationale="Slow."),
            ActionItem(description="Add dark mode.", priority="low",
                       theme_name="UI", rationale="Requested."),
        ],
        sentiment_summary={"positive": 3, "negative": 5, "neutral": 2},
    )
    defaults.update(kwargs)
    return WeeklyInsights(**defaults)


@pytest.fixture
def f():
    return ReportFormatter()


# ── Word count & content constraints ─────────────────────────────────────────

class TestWordCountConstraints:

    def test_max_5_themes_word_count_still_within_limit(self, f):
        """5 themes (max allowed) should still produce ≤250 words."""
        themes = [
            Theme(name=f"Theme {i}", description=f"Description {i}.",
                  review_count=i+1, sentiment=SentimentLabel.NEUTRAL, keywords=[])
            for i in range(5)
        ]
        result = f.format(make_insights(themes=themes))
        assert result["word_count"] <= f.MAX_WORDS

    def test_single_theme_single_quote_single_action(self, f):
        """Minimal content (1 theme, 1 quote, 1 action) should not crash."""
        result = f.format(make_insights(
            themes=[Theme(name="T", description="D.", review_count=1,
                          sentiment=SentimentLabel.NEUTRAL, keywords=[])],
            quotes=[Quote(text="Q.", theme_name="T", rating=3,
                          sentiment=SentimentLabel.NEUTRAL)],
            actions=[ActionItem(description="A.", priority="low",
                                theme_name="T", rationale="R.")],
        ))
        assert result["word_count"] > 0
        assert result["word_count"] <= f.MAX_WORDS

    def test_all_positive_sentiment(self, f):
        """100% positive sentiment — no division error, percentages sum correctly."""
        insights = make_insights()
        insights.sentiment_summary = {"positive": 10, "negative": 0, "neutral": 0}
        result = f.format(insights)
        assert "100%" in result["sections"]["sentiment"]
        assert "0%" in result["sections"]["sentiment"]

    def test_all_negative_sentiment(self, f):
        insights = make_insights()
        insights.sentiment_summary = {"positive": 0, "negative": 10, "neutral": 0}
        result = f.format(insights)
        assert "100%" in result["sections"]["sentiment"]

    def test_single_review_analysed(self, f):
        """total_reviews_analysed=1 should not crash."""
        result = f.format(make_insights(total=1))
        assert "1" in result["sections"]["header"]

    def test_zero_reviews_analysed(self, f):
        result = f.format(make_insights(total=0))
        assert "0" in result["sections"]["header"]


# ── Quote truncation edge cases ───────────────────────────────────────────────

class TestQuoteTruncation:

    def test_quote_exactly_120_chars_not_truncated(self, f):
        exact = "a" * 120
        result = f.format(make_insights(quotes=[
            Quote(text=exact, theme_name="T", rating=3, sentiment=SentimentLabel.NEUTRAL),
            Quote(text="Short.", theme_name="T", rating=4, sentiment=SentimentLabel.POSITIVE),
            Quote(text="Also short.", theme_name="T", rating=2, sentiment=SentimentLabel.NEGATIVE),
        ]))
        assert "..." not in result["sections"]["quotes"]

    def test_quote_121_chars_is_truncated(self, f):
        over = "b" * 121
        result = f.format(make_insights(quotes=[
            Quote(text=over, theme_name="T", rating=3, sentiment=SentimentLabel.NEUTRAL),
            Quote(text="Short.", theme_name="T", rating=4, sentiment=SentimentLabel.POSITIVE),
            Quote(text="Also short.", theme_name="T", rating=2, sentiment=SentimentLabel.NEGATIVE),
        ]))
        assert "..." in result["sections"]["quotes"]

    def test_empty_quote_text_handled(self, f):
        """Empty quote text should not crash."""
        result = f.format(make_insights(quotes=[
            Quote(text="", theme_name="T", rating=3, sentiment=SentimentLabel.NEUTRAL),
            Quote(text="Normal.", theme_name="T", rating=4, sentiment=SentimentLabel.POSITIVE),
            Quote(text="Another.", theme_name="T", rating=2, sentiment=SentimentLabel.NEGATIVE),
        ]))
        assert isinstance(result["plain_text"], str)

    def test_quote_with_special_characters(self, f):
        """Quotes with special chars (apostrophes, dashes, unicode) should render."""
        result = f.format(make_insights(quotes=[
            Quote(text="It's great — really! 🎉", theme_name="T", rating=5,
                  sentiment=SentimentLabel.POSITIVE),
            Quote(text="Normal.", theme_name="T", rating=3, sentiment=SentimentLabel.NEUTRAL),
            Quote(text="Bad.", theme_name="T", rating=1, sentiment=SentimentLabel.NEGATIVE),
        ]))
        assert "great" in result["plain_text"]


# ── Section content correctness ───────────────────────────────────────────────

class TestSectionContent:

    def test_themes_section_numbered_correctly(self, f):
        themes = [
            Theme(name=f"Theme{i}", description="D.", review_count=i,
                  sentiment=SentimentLabel.NEUTRAL, keywords=[])
            for i in range(1, 4)
        ]
        result = f.format(make_insights(themes=themes))
        t = result["sections"]["themes"]
        assert "1." in t
        assert "2." in t
        assert "3." in t

    def test_sentiment_icons_in_themes(self, f):
        themes = [
            Theme(name="Neg", description="D.", review_count=5,
                  sentiment=SentimentLabel.NEGATIVE, keywords=[]),
            Theme(name="Pos", description="D.", review_count=5,
                  sentiment=SentimentLabel.POSITIVE, keywords=[]),
        ]
        result = f.format(make_insights(themes=themes))
        t = result["sections"]["themes"]
        assert SENTIMENT_ICON["negative"] in t
        assert SENTIMENT_ICON["positive"] in t

    def test_priority_icons_in_actions(self, f):
        result = f.format(make_insights())
        a = result["sections"]["actions"]
        assert PRIORITY_ICON["high"] in a
        assert PRIORITY_ICON["medium"] in a
        assert PRIORITY_ICON["low"] in a

    def test_unknown_priority_uses_fallback_icon(self, f):
        """Unknown priority value should not crash — uses ▶ fallback."""
        result = f.format(make_insights(actions=[
            ActionItem(description="Do something.", priority="critical",
                       theme_name="T", rationale="R."),
            ActionItem(description="Do more.", priority="medium",
                       theme_name="T", rationale="R."),
            ActionItem(description="Do less.", priority="low",
                       theme_name="T", rationale="R."),
        ]))
        assert "▶" in result["sections"]["actions"]

    def test_plain_text_sections_joined_with_double_newline(self, f):
        result = f.format(make_insights())
        # Each section separated by \n\n
        assert "\n\n" in result["plain_text"]

    def test_footer_contains_brand_name(self, f):
        result = f.format(make_insights())
        assert "Groww Review Insights Analyzer" in result["sections"]["footer"]

    def test_footer_with_none_generated_at(self, f):
        """None generated_at should fall back to current time without crashing."""
        insights = make_insights()
        insights.generated_at = None
        result = f.format(insights)
        assert "Generated:" in result["sections"]["footer"]


# ── Markdown structure ────────────────────────────────────────────────────────

class TestMarkdownStructure:

    def test_markdown_contains_all_theme_names(self, f):
        themes = [
            Theme(name="Alpha", description="D.", review_count=3,
                  sentiment=SentimentLabel.POSITIVE, keywords=[]),
            Theme(name="Beta", description="D.", review_count=2,
                  sentiment=SentimentLabel.NEGATIVE, keywords=[]),
        ]
        result = f.format(make_insights(themes=themes))
        assert "Alpha" in result["markdown"]
        assert "Beta" in result["markdown"]

    def test_markdown_contains_rationale_for_actions(self, f):
        """Rationale should appear in markdown (not plain text)."""
        result = f.format(make_insights())
        assert "Many affected" in result["markdown"]
        assert "Many affected" not in result["sections"]["actions"]

    def test_markdown_contains_theme_descriptions(self, f):
        """Theme descriptions should appear in markdown."""
        result = f.format(make_insights())
        assert "App crashes" in result["markdown"]

    def test_markdown_ends_with_footer(self, f):
        result = f.format(make_insights())
        assert "Groww Review Insights Analyzer" in result["markdown"].split("\n")[-1]

    def test_markdown_sentiment_table_has_correct_values(self, f):
        result = f.format(make_insights(
            sentiment={"positive": 6, "negative": 3, "neutral": 1}
        ))
        md = result["markdown"]
        assert "6" in md
        assert "3" in md
        assert "1" in md

    def test_markdown_and_plain_text_both_contain_week(self, f):
        result = f.format(make_insights(week="2026-W99"))
        assert "2026-W99" in result["plain_text"]
        assert "2026-W99" in result["markdown"]
