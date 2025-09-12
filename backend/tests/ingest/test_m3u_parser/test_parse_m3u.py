"""Tests for parse_m3u function following atomic design principles.

This module focuses exclusively on testing complete M3U file parsing logic.
Each test validates one specific parsing scenario or edge case.
"""

import pytest
from unittest.mock import patch, MagicMock

from ingest.m3u_parser import parse_m3u, M3uChannel
from fastapi import HTTPException


class TestParseM3u:
    """Atomic tests for parse_m3u function."""

    @pytest.fixture
    def sample_m3u_content(self):
        """Sample M3U content for testing."""
        return """#EXTM3U
#EXTINF:-1 tvg-id="ch1" tvg-name="Channel 1" group-title="News",Channel 1
http://stream1.example.com/live
#EXTINF:-1 tvg-id="ch2" tvg-name="Channel 2" group-title="Sports",Channel 2
http://stream2.example.com/live
#EXTINF:-1 tvg-id="ch3" tvg-name="Movie Channel",Movie Channel
http://stream3.example.com/movie.mp4
"""

    def test_parse_m3u_basic_functionality(self, tmp_path, sample_m3u_content):
        """Basic M3U parsing should return list of M3uChannel objects."""
        m3u_file = tmp_path / "test.m3u"
        m3u_file.write_text(sample_m3u_content)

        channels = parse_m3u(str(m3u_file), "test_source")

        assert len(channels) == 3
        assert all(isinstance(ch, M3uChannel) for ch in channels)

        # Verify first channel
        ch1 = channels[0]
        assert ch1.tvg_id == "ch1"
        assert ch1.name == "Channel 1"
        assert ch1.group == "News"
        assert ch1.stream_url == "http://stream1.example.com/live"
        assert ch1.source == "test_source"
        assert ch1.stream_mode == "live"

        # Verify third channel (on-demand)
        ch3 = channels[2]
        assert ch3.tvg_id == "ch3"
        assert ch3.name == "Movie Channel"
        assert ch3.stream_url == "http://stream3.example.com/movie.mp4"
        assert ch3.stream_mode == "on_demand"

    def test_parse_m3u_with_invalid_lines(self, tmp_path):
        """M3U with invalid lines should skip them gracefully."""
        content = """#EXTM3U
#EXTINF:-1 tvg-id="ch1",Valid Channel
http://valid.stream.com/live
# This is a comment
invalid line without extinf
http://orphaned.stream.com/live
#EXTINF:-1 tvg-id="ch2",Another Valid
http://another.stream.com/live
"""
        m3u_file = tmp_path / "test.m3u"
        m3u_file.write_text(content)

        channels = parse_m3u(str(m3u_file), "test_source")

        # Should only parse valid channel pairs
        assert len(channels) == 2
        assert channels[0].name == "Valid Channel"
        assert channels[1].name == "Another Valid"

    def test_parse_m3u_empty_file(self, tmp_path):
        """Empty M3U file should return empty list."""
        m3u_file = tmp_path / "empty.m3u"
        m3u_file.write_text("")

        channels = parse_m3u(str(m3u_file), "test_source")

        assert channels == []

    def test_parse_m3u_only_header(self, tmp_path):
        """M3U with only header should return empty list."""
        m3u_file = tmp_path / "header_only.m3u"
        m3u_file.write_text("#EXTM3U\n")

        channels = parse_m3u(str(m3u_file), "test_source")

        assert channels == []

    def test_parse_m3u_missing_stream_urls(self, tmp_path):
        """EXTINF lines without corresponding stream URLs should be skipped."""
        content = """#EXTM3U
#EXTINF:-1 tvg-id="ch1",Channel 1
#EXTINF:-1 tvg-id="ch2",Channel 2
http://stream2.example.com/live
#EXTINF:-1 tvg-id="ch3",Channel 3
"""
        m3u_file = tmp_path / "test.m3u"
        m3u_file.write_text(content)

        channels = parse_m3u(str(m3u_file), "test_source")

        # Only channel 2 should be parsed (has both EXTINF and URL)
        assert len(channels) == 1
        assert channels[0].name == "Channel 2"

    def test_parse_m3u_with_whitespace_urls(self, tmp_path):
        """Stream URLs with whitespace should be trimmed."""
        content = """#EXTM3U
#EXTINF:-1 tvg-id="ch1",Channel 1
  http://stream1.example.com/live  
#EXTINF:-1 tvg-id="ch2",Channel 2
\thttp://stream2.example.com/live\t
"""
        m3u_file = tmp_path / "test.m3u"
        m3u_file.write_text(content)

        channels = parse_m3u(str(m3u_file), "test_source")

        assert len(channels) == 2
        assert channels[0].stream_url == "http://stream1.example.com/live"
        assert channels[1].stream_url == "http://stream2.example.com/live"

    def test_parse_m3u_with_blank_lines(self, tmp_path):
        """M3U with blank lines should handle them gracefully."""
        content = """#EXTM3U

#EXTINF:-1 tvg-id="ch1",Channel 1

http://stream1.example.com/live


#EXTINF:-1 tvg-id="ch2",Channel 2

http://stream2.example.com/live

"""
        m3u_file = tmp_path / "test.m3u"
        m3u_file.write_text(content)

        channels = parse_m3u(str(m3u_file), "test_source")

        assert len(channels) == 2
        assert channels[0].name == "Channel 1"
        assert channels[1].name == "Channel 2"

    def test_parse_m3u_with_unhandled_tags(self, tmp_path):
        """M3U with unhandled tags should still parse valid channels."""
        content = """#EXTM3U
#EXT-X-VERSION:3
#EXTINF:-1 tvg-id="ch1" custom-attr="value",Channel 1
http://stream1.example.com/live
#EXT-X-STREAM-INF:BANDWIDTH=1000000
#EXTINF:-1 tvg-id="ch2",Channel 2
http://stream2.example.com/live
"""
        m3u_file = tmp_path / "test.m3u"
        m3u_file.write_text(content)

        channels = parse_m3u(str(m3u_file), "test_source")

        # Should still parse valid channels despite unhandled tags
        assert len(channels) == 2
        assert channels[0].name == "Channel 1"
        assert channels[1].name == "Channel 2"
        assert channels[0].tvg_id == "ch1"
        assert channels[1].tvg_id == "ch2"

    def test_parse_m3u_with_task_id_parameter(self, tmp_path, sample_m3u_content):
        """M3U parsing with task_id parameter should work without errors."""
        m3u_file = tmp_path / "test.m3u"
        m3u_file.write_text(sample_m3u_content)

        # Should not raise any exceptions when task_id is provided
        channels = parse_m3u(str(m3u_file), "test_source", task_id="test_task")

        assert len(channels) == 3
        # Verify basic functionality still works with task_id
        assert channels[0].name == "Channel 1"
        assert channels[0].source == "test_source"

    def test_parse_m3u_file_encoding(self, tmp_path):
        """M3U file should be read with UTF-8 encoding."""
        content = """#EXTM3U
#EXTINF:-1 tvg-id="ch1",Chaîne française
http://stream1.example.com/live
#EXTINF:-1 tvg-id="ch2",Канал русский
http://stream2.example.com/live
"""
        m3u_file = tmp_path / "test.m3u"
        m3u_file.write_text(content, encoding="utf-8")

        channels = parse_m3u(str(m3u_file), "test_source")

        assert len(channels) == 2
        assert channels[0].name == "Chaîne française"
        assert channels[1].name == "Канал русский"

    def test_parse_m3u_large_file_performance(self, tmp_path):
        """Large M3U file should parse efficiently."""
        # Generate content for 1000 channels
        lines = ["#EXTM3U"]
        for i in range(1000):
            lines.append(f'#EXTINF:-1 tvg-id="ch{i}",Channel {i}')
            lines.append(f"http://stream{i}.example.com/live")

        content = "\n".join(lines)
        m3u_file = tmp_path / "large.m3u"
        m3u_file.write_text(content)

        channels = parse_m3u(str(m3u_file), "test_source")

        assert len(channels) == 1000
        assert channels[0].name == "Channel 0"
        assert channels[999].name == "Channel 999"

    def test_parse_m3u_integration_with_validation(self, tmp_path):
        """Integration test ensuring parse_m3u works with validation logic."""
        content = """#EXTM3U
#EXTINF:-1 tvg-id="valid1" group-title="News",Valid Channel
http://valid.stream.com/live
#EXTINF:-1 tvg-id="",Channel with empty ID
http://empty.id.com/live
#EXTINF:-1 tvg-id="valid2",Channel without URL
#EXTINF:-1 tvg-id="valid3",Valid Movie
http://movie.stream.com/video.mp4
"""
        m3u_file = tmp_path / "test.m3u"
        m3u_file.write_text(content)

        channels = parse_m3u(str(m3u_file), "test_source")

        # Should parse 3 valid channels (skip the one without URL)
        assert len(channels) == 3

        # Verify validation worked correctly
        assert channels[0].tvg_id == "valid1"
        assert channels[0].group == "News"
        assert channels[0].stream_mode == "live"

        assert (
            channels[1].tvg_id == "Channel with empty ID"
        )  # Empty tvg_id gets channel name
        assert channels[1].stream_mode == "live"

        assert channels[2].tvg_id == "valid3"
        assert channels[2].stream_mode == "on_demand"  # .mp4 extension

    def test_file_not_found_raises_exception(self):
        """Non-existent file should raise HTTPException."""

        with pytest.raises(HTTPException) as exc_info:
            parse_m3u("/non/existent/file.m3u", source="test_source")

        assert exc_info.value.status_code == 500
        assert "Error parsing M3U file" in str(exc_info.value.detail)
