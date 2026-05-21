"""
Tests for PII scrubber utility.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from shared.pii_scrubber import scrub, scrub_review_dict


class TestScrubEmails:
    def test_removes_email(self):
        assert scrub("Contact me at user@example.com please") == "Contact me at [EMAIL] please"

    def test_removes_multiple_emails(self):
        result = scrub("a@b.com and c@d.org")
        assert "[EMAIL]" in result
        assert "a@b.com" not in result
        assert "c@d.org" not in result

    def test_no_false_positive_on_normal_text(self):
        text = "This app is great"
        assert scrub(text) == text


class TestScrubPhones:
    def test_removes_indian_mobile(self):
        result = scrub("Call me on 9876543210 for help")
        assert "9876543210" not in result
        assert "[PHONE]" in result

    def test_removes_indian_mobile_with_country_code(self):
        result = scrub("Reach me at +91 9876543210")
        assert "9876543210" not in result

    def test_removes_us_style_phone(self):
        result = scrub("Call 123-456-7890 now")
        assert "123-456-7890" not in result
        assert "[PHONE]" in result


class TestScrubURLs:
    def test_removes_http_url(self):
        result = scrub("Visit https://example.com for more")
        assert "https://example.com" not in result
        assert "[URL]" in result

    def test_removes_www_url(self):
        result = scrub("Go to www.groww.in for details")
        assert "www.groww.in" not in result
        assert "[URL]" in result

    def test_removes_http_url_with_path(self):
        result = scrub("See http://example.com/path?q=1")
        assert "http://example.com" not in result


class TestScrubMentions:
    def test_removes_at_mention(self):
        result = scrub("Thanks @GrowwSupport for the help")
        assert "@GrowwSupport" not in result
        assert "[USER]" in result

    def test_removes_multiple_mentions(self):
        result = scrub("@user1 and @user2 are great")
        assert "@user1" not in result
        assert "@user2" not in result


class TestScrubAadhaar:
    def test_removes_aadhaar_number(self):
        result = scrub("My ID is 1234 5678 9012")
        assert "1234 5678 9012" not in result
        assert "[ID]" in result

    def test_removes_aadhaar_with_dashes(self):
        result = scrub("Aadhaar: 1234-5678-9012")
        assert "1234-5678-9012" not in result


class TestScrubCombined:
    def test_scrubs_multiple_pii_types(self):
        text = "Email user@test.com or call 9876543210 or visit https://test.com"
        result = scrub(text)
        assert "user@test.com" not in result
        assert "9876543210" not in result
        assert "https://test.com" not in result

    def test_empty_string_returns_empty(self):
        assert scrub("") == ""

    def test_none_returns_none(self):
        assert scrub(None) is None

    def test_clean_text_unchanged(self):
        text = "The app crashes on startup. Please fix the login bug."
        assert scrub(text) == text


class TestScrubReviewDict:
    def test_scrubs_text_and_title(self):
        review = {
            "id": "abc",
            "source": "google_play",
            "rating": 3,
            "title": "Contact @support",
            "text": "Email me at user@test.com",
            "date": "2026-01-01",
            "version": "1.0",
            "processed": False,
        }
        result = scrub_review_dict(review)
        assert "[USER]" in result["title"]
        assert "[EMAIL]" in result["text"]

    def test_does_not_mutate_original(self):
        review = {"title": "Hi @user", "text": "Call 9876543210"}
        original_title = review["title"]
        scrub_review_dict(review)
        assert review["title"] == original_title

    def test_preserves_non_pii_fields(self):
        review = {
            "id": "xyz",
            "source": "google_play",
            "rating": 5,
            "title": "Great app",
            "text": "Works perfectly",
            "date": "2026-01-01",
            "version": "2.0",
            "processed": False,
        }
        result = scrub_review_dict(review)
        assert result["id"] == "xyz"
        assert result["rating"] == 5
        assert result["version"] == "2.0"
        assert result["text"] == "Works perfectly"
