"""Unit tests for SessionTracker."""

import pytest
from src.session import SessionTracker


class TestSessionTracker:
    """Tests for SessionTracker."""

    def setup_method(self):
        self.tracker = SessionTracker()

    def test_track_and_get_referral(self):
        self.tracker.track("1.2.3.4", "google.com", "ipod")
        result = self.tracker.get_referral("1.2.3.4")
        assert result == ("google.com", "ipod")

    def test_first_referral_is_kept(self):
        """Only the first search engine referral should be stored per IP."""
        self.tracker.track("1.2.3.4", "google.com", "ipod")
        self.tracker.track("1.2.3.4", "bing.com", "zune")
        result = self.tracker.get_referral("1.2.3.4")
        assert result == ("google.com", "ipod")

    def test_unknown_ip_returns_none(self):
        assert self.tracker.get_referral("9.9.9.9") is None

    def test_has_referral_true(self):
        self.tracker.track("1.2.3.4", "google.com", "ipod")
        assert self.tracker.has_referral("1.2.3.4") is True

    def test_has_referral_false(self):
        assert self.tracker.has_referral("9.9.9.9") is False

    def test_multiple_ips_tracked_independently(self):
        self.tracker.track("1.1.1.1", "google.com", "ipod")
        self.tracker.track("2.2.2.2", "bing.com", "zune")
        assert self.tracker.get_referral("1.1.1.1") == ("google.com", "ipod")
        assert self.tracker.get_referral("2.2.2.2") == ("bing.com", "zune")
