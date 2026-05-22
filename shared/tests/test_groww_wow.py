"""Tests for Groww product map and week-over-week delta."""
from shared.groww_product_map import (
    cluster_by_keywords,
    normalize_area_name,
    normalize_themes_from_llm,
    themes_to_area_counts,
)
from shared.week_over_week import compute_week_over_week, previous_week_id


def test_normalize_area_name_canonical():
    assert normalize_area_name("Stocks & F&O") == "Stocks & F&O"
    assert normalize_area_name("mutual funds") == "Mutual Funds & SIP"
    assert normalize_area_name("withdrawal delays") == "Withdrawals & Settlement"


def test_cluster_by_keywords_fintech():
    reviews = [
        {"title": "", "text": "withdrawal stuck for 5 days", "rating": 1},
        {"title": "", "text": "great mutual fund SIP experience", "rating": 5},
        {"title": "", "text": "chart candles lag on commodity", "rating": 2},
    ]
    themes = cluster_by_keywords(reviews)
    names = {t.name for t in themes}
    assert "Withdrawals & Settlement" in names or "Mutual Funds & SIP" in names


def test_normalize_themes_from_llm_merges_duplicates():
    items = [
        {"name": "stocks", "description": "Trading issues.", "review_count": 10,
         "sentiment": "negative", "keywords": ["stock"]},
        {"name": "Stocks & F&O", "description": "More trading.", "review_count": 5,
         "sentiment": "negative", "keywords": ["fno"]},
    ]
    themes = normalize_themes_from_llm(items, 15)
    assert len(themes) == 1
    assert themes[0].name == "Stocks & F&O"
    assert themes[0].review_count == 15


def test_themes_to_area_counts():
    counts = themes_to_area_counts([
        {"name": "Trust & Fraud", "review_count": 12},
        {"name": "Unknown", "review_count": 3},
    ])
    assert counts["Trust & Fraud"] == 12


def test_previous_week_id():
    assert previous_week_id("2026-W21") == "2026-W20"


def test_compute_week_over_week_with_prior():
    current = {
        "week": "2026-W21",
        "sentiment_summary": {"positive": 30, "negative": 70, "neutral": 0},
        "themes": [
            {"name": "Trust & Fraud", "review_count": 40},
            {"name": "Stocks & F&O", "review_count": 20},
        ],
    }
    prior = {
        "week": "2026-W20",
        "sentiment_summary": {"positive": 40, "negative": 60, "neutral": 0},
        "themes": [
            {"name": "Trust & Fraud", "review_count": 25},
            {"name": "Charts & UX", "review_count": 15},
        ],
    }
    wow = compute_week_over_week(current, prior)
    assert wow["has_prior_week"] is True
    rising_names = [t["name"] for t in wow["rising_themes"]]
    assert "Stocks & F&O" in rising_names
    assert "Trust & Fraud" in rising_names
    assert wow["sentiment_delta"]["positive_pct_delta"] == -10


def test_compute_week_over_week_no_prior():
    wow = compute_week_over_week({"week": "2026-W21", "sentiment_summary": {}, "themes": []}, None)
    assert wow["has_prior_week"] is False
