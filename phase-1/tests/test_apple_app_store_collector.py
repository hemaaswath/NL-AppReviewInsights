"""
Tests for Apple App Store review collector.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from apple_app_store_collector import AppleAppStoreCollector
from shared.models import ReviewSource, ReviewCollection
from bs4 import BeautifulSoup


def make_entry_xml(
    author="Test User",
    title="Great app",
    content="This is a great app for investing and trading stocks easily",
    rating="5",
    updated=None,
    version="2.0.0",
):
    """Helper to build an Apple RSS <entry> XML string."""
    if updated is None:
        updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:im="http://itunes.apple.com/rss">
<entry>
    <author><name>{author}</name></author>
    <title>{title}</title>
    <content type="text">{content}</content>
    <im:rating>{rating}</im:rating>
    <updated>{updated}</updated>
    <im:version>{version}</im:version>
</entry>
</feed>"""


def parse_entry(xml_string):
    """Parse the first <entry> from an XML string."""
    soup = BeautifulSoup(xml_string, "xml")
    return soup.find("entry")


class TestAppleAppStoreCollectorInit:
    """Tests for collector initialisation."""

    def test_initialization_defaults(self):
        """Stores app_id and weeks_back correctly."""
        collector = AppleAppStoreCollector(app_id="123456", weeks_back=12)
        assert collector.app_id == "123456"
        assert collector.weeks_back == 12
        assert collector.cutoff_date is not None

    def test_cutoff_date_calculation(self):
        """Cutoff date is approximately (now - weeks_back)."""
        weeks_back = 8
        collector = AppleAppStoreCollector(app_id="123456", weeks_back=weeks_back)
        expected = datetime.now(timezone.utc) - timedelta(weeks=weeks_back)
        diff = abs((collector.cutoff_date - expected).total_seconds())
        assert diff < 2.0

    def test_cutoff_date_is_timezone_aware(self):
        """Cutoff date must be timezone-aware."""
        collector = AppleAppStoreCollector(app_id="123456")
        assert collector.cutoff_date.tzinfo is not None


class TestAppleAppStoreCollectorParseReview:
    """Tests for _parse_review."""

    @pytest.fixture
    def collector(self):
        return AppleAppStoreCollector(app_id="123456", weeks_back=52)

    def test_parse_valid_review(self, collector):
        """A fully valid XML entry produces a Review object."""
        entry = parse_entry(make_entry_xml())
        review = collector._parse_review(entry)
        assert review is not None
        assert review.source == ReviewSource.APPLE_APP_STORE
        assert review.rating == 5
        assert review.title == "Great app"
        assert review.text == "This is a great app for investing and trading stocks easily"
        assert review.version == "2.0.0"
        assert review.processed is False

    def test_parse_review_id_generated(self, collector):
        """Review ID is generated and non-empty."""
        entry = parse_entry(make_entry_xml())
        review = collector._parse_review(entry)
        assert review is not None
        assert review.id is not None
        assert len(review.id) > 0

    def test_parse_review_all_ratings(self, collector):
        """Ratings 1-5 are all accepted."""
        for rating in range(1, 6):
            entry = parse_entry(make_entry_xml(rating=str(rating)))
            review = collector._parse_review(entry)
            assert review is not None, f"Rating {rating} should be valid"
            assert review.rating == rating

    def test_parse_review_invalid_rating_zero(self, collector):
        """Rating 0 is invalid — returns None."""
        entry = parse_entry(make_entry_xml(rating="0"))
        review = collector._parse_review(entry)
        assert review is None

    def test_parse_review_empty_content(self, collector):
        """Empty content returns None."""
        entry = parse_entry(make_entry_xml(content=""))
        review = collector._parse_review(entry)
        assert review is None

    def test_parse_review_old_date_filtered(self):
        """Review older than cutoff is filtered out."""
        collector = AppleAppStoreCollector(app_id="123456", weeks_back=1)
        old_date = (datetime.now(timezone.utc) - timedelta(weeks=20)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        entry = parse_entry(make_entry_xml(updated=old_date))
        review = collector._parse_review(entry)
        assert review is None

    def test_parse_review_within_cutoff_accepted(self, collector):
        """Review within cutoff window is accepted."""
        recent_date = (datetime.now(timezone.utc) - timedelta(days=3)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        entry = parse_entry(make_entry_xml(updated=recent_date))
        review = collector._parse_review(entry)
        assert review is not None

    def test_parse_review_missing_version(self, collector):
        """Missing version tag does not crash — version is empty string."""
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:im="http://itunes.apple.com/rss">
<entry>
    <author><name>User</name></author>
    <title>Title</title>
    <content type="text">Some review text with enough words to pass normalization rules</content>
    <im:rating>4</im:rating>
    <updated>{datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}</updated>
</entry>
</feed>"""
        entry = parse_entry(xml)
        review = collector._parse_review(entry)
        assert review is not None
        assert review.version == ""

    def test_parse_review_malformed_date_fallback(self, collector):
        """Malformed date falls back to now() without crashing."""
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:im="http://itunes.apple.com/rss">
<entry>
    <author><name>User</name></author>
    <title>Title</title>
    <content type="text">Some review text with enough words to pass normalization rules</content>
    <im:rating>3</im:rating>
    <updated>not-a-date</updated>
    <im:version>1.0</im:version>
</entry>
</feed>"""
        entry = parse_entry(xml)
        review = collector._parse_review(entry)
        # Falls back to now() — should be within cutoff
        assert review is not None

    def test_parse_review_special_characters(self, collector):
        """Reviews with special characters are parsed correctly."""
        entry = parse_entry(
            make_entry_xml(
                content="Great app! Works well & fast. 100% recommended.",
                title="5/5 stars",
            )
        )
        review = collector._parse_review(entry)
        assert review is not None
        assert "Great app" in review.text


class TestAppleAppStoreCollectorFetch:
    """Tests for _fetch_reviews_page and collect_reviews using mocks."""

    @pytest.fixture
    def collector(self):
        return AppleAppStoreCollector(app_id="123456", weeks_back=52)

    def _make_feed_xml(self, num_reviews=3):
        """Build a full RSS feed XML with app info entry + review entries."""
        recent = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        entries = """<entry><title>App Info</title></entry>"""  # first entry = app info
        for i in range(num_reviews):
            entries += f"""
<entry>
    <author><name>User {i}</name></author>
    <title>Review {i}</title>
    <content type="text">Review content {i}</content>
    <im:rating>{(i % 5) + 1}</im:rating>
    <updated>{recent}</updated>
    <im:version>2.0.{i}</im:version>
</entry>"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:im="http://itunes.apple.com/rss">{entries}</feed>"""

    def test_collect_returns_review_collection(self, collector):
        """collect_reviews returns a ReviewCollection."""
        with patch.object(
            collector, "_fetch_reviews_page", return_value=self._make_feed_xml(3)
        ):
            result = collector.collect_reviews(max_reviews=3)
        assert isinstance(result, ReviewCollection)
        assert result.source == ReviewSource.APPLE_APP_STORE

    def test_collect_skips_first_entry(self, collector):
        """First entry (app info) is skipped; only review entries are returned."""
        empty_feed = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:im="http://itunes.apple.com/rss"></feed>"""
        # First call returns 1 app-info entry + 3 review entries; second call returns empty feed
        with patch.object(
            collector,
            "_fetch_reviews_page",
            side_effect=[self._make_feed_xml(3), empty_feed],
        ):
            result = collector.collect_reviews(max_reviews=10)
        assert len(result.reviews) == 3  # app-info entry skipped, 3 reviews collected

    def test_collect_respects_max_reviews(self, collector):
        """collect_reviews stops at max_reviews."""
        with patch.object(
            collector, "_fetch_reviews_page", return_value=self._make_feed_xml(10)
        ):
            result = collector.collect_reviews(max_reviews=2)
        assert len(result.reviews) <= 2

    def test_collect_handles_fetch_error_gracefully(self, collector):
        """Fetch errors are caught and an empty collection is returned."""
        with patch.object(
            collector, "_fetch_reviews_page", side_effect=Exception("Network error")
        ):
            result = collector.collect_reviews(max_reviews=5)
        assert isinstance(result, ReviewCollection)
        assert len(result.reviews) == 0

    def test_collect_stops_on_empty_feed(self, collector):
        """Stops when feed has no entries."""
        empty_feed = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:im="http://itunes.apple.com/rss"></feed>"""
        with patch.object(
            collector, "_fetch_reviews_page", return_value=empty_feed
        ):
            result = collector.collect_reviews()
        assert len(result.reviews) == 0
