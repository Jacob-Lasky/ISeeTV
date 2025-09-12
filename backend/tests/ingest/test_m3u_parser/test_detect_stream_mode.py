"""Tests for detect_stream_mode function following atomic design principles.

This module focuses exclusively on testing the stream mode detection logic.
Each test validates one specific URL pattern or edge case.
"""

import pytest

from ingest.m3u_parser import detect_stream_mode


class TestDetectStreamMode:
    """Atomic tests for detect_stream_mode function."""

    def test_empty_url_returns_live(self):
        """Empty URL should default to live mode."""
        assert detect_stream_mode("") == "live"

    def test_none_url_returns_live(self):
        """None URL should default to live mode."""
        assert detect_stream_mode(None) == "live"

    def test_http_streaming_url_returns_live(self):
        """HTTP streaming URLs should return live mode."""
        assert detect_stream_mode("http://example.com/stream") == "live"

    def test_https_streaming_url_returns_live(self):
        """HTTPS streaming URLs should return live mode."""
        assert detect_stream_mode("https://example.com/stream") == "live"

    @pytest.mark.parametrize(
        "extension",
        [
            ".avi",
            ".mkv",
            ".mp4",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
            ".3gp",
            ".ogv",
            ".ts",
            ".m2ts",
            ".vob",
            ".divx",
        ],
    )
    def test_on_demand_extensions_return_on_demand(self, extension):
        """Video file extensions should return on_demand mode."""
        url = f"http://example.com/video{extension}"
        assert detect_stream_mode(url) == "on_demand"

    def test_case_insensitive_extension_detection(self):
        """Extension detection should be case insensitive."""
        assert detect_stream_mode("http://example.com/video.MP4") == "on_demand"
        assert detect_stream_mode("http://example.com/video.MKV") == "on_demand"

    def test_url_with_query_parameters_ignores_params(self):
        """Query parameters should be ignored when detecting extensions."""
        url = "http://example.com/video.mp4?token=abc123&quality=hd"
        assert detect_stream_mode(url) == "on_demand"

    def test_url_without_extension_returns_live(self):
        """URLs without file extensions should return live mode."""
        assert detect_stream_mode("http://example.com/stream/channel1") == "live"

    def test_m3u8_playlist_returns_live(self):
        """M3U8 playlist URLs should return live mode."""
        assert detect_stream_mode("http://example.com/playlist.m3u8") == "live"
