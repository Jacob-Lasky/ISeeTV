"""Tests for validate_m3u_channel function following atomic design principles.

This module focuses exclusively on testing M3U channel validation logic.
Each test validates one specific validation scenario or edge case.
"""

import pytest
from unittest.mock import patch

from ingest.m3u_parser import validate_m3u_channel
from models.models import M3uChannel


class TestValidateM3uChannel:
    """Atomic tests for validate_m3u_channel function."""

    def test_valid_channel_creation(self):
        """Valid channel data should create M3uChannel object."""
        attrs = {
            "tvg-id": "channel1",
            "tvg-name": "Channel 1",
            "tvg-logo": "http://logo.png",
            "group-title": "Entertainment",
        }
        channel_name = "Channel 1"
        stream_url = "http://example.com/stream"

        channel = validate_m3u_channel(attrs, channel_name, stream_url)

        assert isinstance(channel, M3uChannel)
        assert channel.tvg_id == "channel1"
        assert channel.name == "Channel 1"
        assert channel.stream_url == "http://example.com/stream"
        assert channel.logo_url == "http://logo.png"
        assert channel.group == "Entertainment"
        assert channel.source == "m3u"  # Default source

    def test_missing_stream_url_returns_none(self):
        """Missing stream URL should return None."""
        attrs = {"tvg-id": "channel1"}
        channel_name = "Channel 1"

        assert validate_m3u_channel(attrs, channel_name, None) is None
        assert validate_m3u_channel(attrs, channel_name, "") is None
        assert validate_m3u_channel(attrs, channel_name, "   ") is None

    def test_missing_tvg_id_uses_channel_name(self):
        """Missing tvg-id should use channel name as fallback."""
        attrs = {"tvg-name": "Channel 1"}
        channel_name = "Channel 1"
        stream_url = "http://example.com/stream"

        channel = validate_m3u_channel(attrs, channel_name, stream_url)

        assert channel.tvg_id == "Channel 1"

    def test_empty_tvg_id_uses_channel_name(self):
        """Empty tvg-id should use channel name as fallback."""
        attrs = {"tvg-id": "", "tvg-name": "Channel 1"}
        channel_name = "Channel 1"
        stream_url = "http://example.com/stream"

        channel = validate_m3u_channel(attrs, channel_name, stream_url)

        assert channel.tvg_id == "Channel 1"

    def test_missing_tvg_name_uses_channel_name(self):
        """Missing tvg-name should use channel name as fallback."""
        attrs = {"tvg-id": "ch1"}
        channel_name = "Channel Name"
        stream_url = "http://example.com/stream"

        channel = validate_m3u_channel(attrs, channel_name, stream_url)

        assert channel.name == "Channel Name"

    def test_empty_tvg_name_uses_channel_name(self):
        """Empty tvg-name should use channel name as fallback."""
        attrs = {"tvg-id": "ch1", "tvg-name": ""}
        channel_name = "Channel Name"
        stream_url = "http://example.com/stream"

        channel = validate_m3u_channel(attrs, channel_name, stream_url)

        assert channel.name == "Channel Name"

    def test_optional_fields_default_to_none(self):
        """Optional fields should default to None when missing."""
        attrs = {"tvg-id": "ch1"}
        channel_name = "Channel"
        stream_url = "http://example.com/stream"

        channel = validate_m3u_channel(attrs, channel_name, stream_url)

        assert channel.logo_url is None
        assert channel.group is None

    def test_empty_optional_fields_default_to_none(self):
        """Empty optional fields should default to None."""
        attrs = {"tvg-id": "ch1", "tvg-logo": "", "group-title": ""}
        channel_name = "Channel"
        stream_url = "http://example.com/stream"

        channel = validate_m3u_channel(attrs, channel_name, stream_url)

        assert channel.logo_url is None
        assert channel.group is None

    def test_whitespace_trimming(self):
        """Whitespace should be trimmed from all fields."""
        attrs = {
            "tvg-id": "  ch1  ",
            "tvg-name": "  Channel Name  ",
            "tvg-logo": "  http://logo.png  ",
            "group-title": "  Sports  ",
        }
        channel_name = "  Channel  "
        stream_url = "  http://example.com/stream  "

        channel = validate_m3u_channel(attrs, channel_name, stream_url)

        assert channel.tvg_id == "ch1"
        assert channel.name == "Channel Name"
        assert channel.stream_url == "http://example.com/stream"
        assert channel.logo_url == "http://logo.png"
        assert channel.group == "Sports"

    @patch("ingest.m3u_parser.detect_stream_mode")
    def test_stream_mode_detection_called(self, mock_detect):
        """Stream mode detection should be called with stream URL."""
        mock_detect.return_value = "live"

        attrs = {"tvg-id": "ch1"}
        channel_name = "Channel"
        stream_url = "http://example.com/stream"

        channel = validate_m3u_channel(attrs, channel_name, stream_url)

        mock_detect.assert_called_once_with(stream_url)
        assert channel.stream_mode == "live"

    def test_default_source_value(self):
        """validate_m3u_channel should use default 'm3u' source."""
        attrs = {"tvg-id": "ch1"}
        channel_name = "Channel"
        stream_url = "http://example.com/stream"

        channel = validate_m3u_channel(attrs, channel_name, stream_url)

        assert channel.source == "m3u"  # Default hardcoded value

    def test_validation_with_all_attributes(self):
        """Validation should handle all possible EXTINF attributes correctly."""
        attrs = {
            "tvg-id": "sports1",
            "tvg-name": "Sports Channel",
            "tvg-logo": "http://logo.sports.com/logo.png",
            "group-title": "Sports",
            "tvg-country": "US",
            "tvg-language": "English",
            "custom-attr": "custom-value"  # Should be ignored
        }
        channel_name = "ESPN"
        stream_url = "http://sports.stream.com/espn"

        channel = validate_m3u_channel(attrs, channel_name, stream_url)

        assert channel.tvg_id == "sports1"
        assert channel.name == "Sports Channel"  # Uses tvg-name over channel_name
        assert channel.stream_url == "http://sports.stream.com/espn"
        assert channel.logo_url == "http://logo.sports.com/logo.png"
        assert channel.group == "Sports"
        assert channel.source == "m3u"  # Default hardcoded value
        # Custom attributes should not affect the channel object
