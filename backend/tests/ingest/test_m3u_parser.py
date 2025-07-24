"""Comprehensive tests for M3U parser following atomic design principles.

Each test function has single responsibility and tests one specific behavior.
Tests are organized by function and cover edge cases, error conditions, and normal operation.
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from ingest.m3u_parser import (
    EXPECTED_EXTINF_KEYS,
    EXPECTED_M3U_TAGS,
    M3uValidationResults,
    detect_stream_mode,
    parse_extinf_line,
    parse_m3u,
    validate_m3u_channel,
)
from models.models import M3uChannel


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


class TestParseExtinfLine:
    """Atomic tests for parse_extinf_line function."""

    def test_basic_extinf_parsing(self):
        """Basic EXTINF line should parse correctly."""
        line = '#EXTINF:-1 tvg-id="channel1" tvg-name="Channel 1",Channel 1'
        attrs, name = parse_extinf_line(line)

        assert attrs == {"tvg-id": "channel1", "tvg-name": "Channel 1"}
        assert name == "Channel 1"

    def test_extinf_with_quoted_values(self):
        """EXTINF with quoted attribute values should parse correctly."""
        line = '#EXTINF:-1 tvg-id="ch1" tvg-logo="http://logo.png" group-title="Sports",ESPN'
        attrs, name = parse_extinf_line(line)

        expected_attrs = {
            "tvg-id": "ch1",
            "tvg-logo": "http://logo.png",
            "group-title": "Sports",
        }
        assert attrs == expected_attrs
        assert name == "ESPN"

    def test_extinf_with_unquoted_values(self):
        """EXTINF with unquoted attribute values should parse correctly."""
        line = "#EXTINF:-1 tvg-id=channel1 group-title=News,CNN"
        attrs, name = parse_extinf_line(line)

        assert attrs == {"tvg-id": "channel1", "group-title": "News"}
        assert name == "CNN"

    def test_extinf_mixed_quoted_unquoted(self):
        """EXTINF with mixed quoted and unquoted values should parse correctly."""
        line = (
            '#EXTINF:-1 tvg-id="ch1" group-title=Sports tvg-name="Channel Name",Channel'
        )
        attrs, name = parse_extinf_line(line)

        expected_attrs = {
            "tvg-id": "ch1",
            "group-title": "Sports",
            "tvg-name": "Channel Name",
        }
        assert attrs == expected_attrs
        assert name == "Channel"

    def test_extinf_no_comma_returns_empty_attrs(self):
        """EXTINF line without comma should return empty attrs and full line as name."""
        line = '#EXTINF:-1 tvg-id="channel1"'
        attrs, name = parse_extinf_line(line)

        assert attrs == {}
        assert name == '-1 tvg-id="channel1"'

    def test_extinf_empty_channel_name(self):
        """EXTINF with empty channel name should handle gracefully."""
        line = '#EXTINF:-1 tvg-id="channel1",'
        attrs, name = parse_extinf_line(line)

        assert attrs == {"tvg-id": "channel1"}
        assert name == ""

    def test_extinf_channel_name_with_comma(self):
        """Channel name containing comma should use last comma as separator."""
        line = '#EXTINF:-1 tvg-id="ch1",Channel, Name With Comma'
        attrs, name = parse_extinf_line(line)

        assert attrs == {"tvg-id": "ch1"}
        assert name == "Name With Comma"

    def test_extinf_empty_attribute_values(self):
        """Empty attribute values should be handled correctly."""
        line = '#EXTINF:-1 tvg-id="" tvg-name="" group-title="",Channel'
        attrs, name = parse_extinf_line(line)

        expected_attrs = {"tvg-id": "", "tvg-name": "", "group-title": ""}
        assert attrs == expected_attrs
        assert name == "Channel"

    def test_extinf_with_duration_and_attributes(self):
        """EXTINF with duration and multiple attributes should parse correctly."""
        line = '#EXTINF:3600 tvg-id="movie1" tvg-logo="logo.png",Movie Title'
        attrs, name = parse_extinf_line(line)

        assert attrs == {"tvg-id": "movie1", "tvg-logo": "logo.png"}
        assert name == "Movie Title"


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


class TestParseM3u:
    """Atomic tests for parse_m3u function."""

    def create_temp_m3u_file(self, content: str) -> str:
        """Helper function to create temporary M3U file for testing."""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".m3u", delete=False)
        temp_file.write(content)
        temp_file.close()
        return temp_file.name

    def teardown_method(self):
        """Clean up any temporary files after each test."""
        # This will be called after each test method

    def test_basic_m3u_parsing(self):
        """Basic M3U file should parse correctly."""
        content = """#EXTM3U
#EXTINF:-1 tvg-id="channel1" tvg-name="Channel 1" group-title="Entertainment",Channel 1
http://example.com/stream1
#EXTINF:-1 tvg-id="channel2" tvg-name="Channel 2" group-title="Sports",Channel 2
http://example.com/stream2
"""
        temp_file = self.create_temp_m3u_file(content)

        try:
            channels = parse_m3u(temp_file, source="test_source")

            assert len(channels) == 2

            # Test first channel
            assert channels[0].tvg_id == "channel1"
            assert channels[0].name == "Channel 1"
            assert channels[0].stream_url == "http://example.com/stream1"
            assert channels[0].group == "Entertainment"
            assert channels[0].source == "test_source"

            # Test second channel
            assert channels[1].tvg_id == "channel2"
            assert channels[1].name == "Channel 2"
            assert channels[1].stream_url == "http://example.com/stream2"
            assert channels[1].group == "Sports"
            assert channels[1].source == "test_source"
        finally:
            os.unlink(temp_file)

    def test_empty_m3u_file(self):
        """Empty M3U file should return empty list."""
        content = ""
        temp_file = self.create_temp_m3u_file(content)

        try:
            channels = parse_m3u(temp_file, source="test_source")
            assert channels == []
        finally:
            os.unlink(temp_file)

    def test_m3u_with_only_header(self):
        """M3U file with only header should return empty list."""
        content = "#EXTM3U\n"
        temp_file = self.create_temp_m3u_file(content)

        try:
            channels = parse_m3u(temp_file, source="test_source")
            assert channels == []
        finally:
            os.unlink(temp_file)

    def test_m3u_with_empty_lines(self):
        """M3U file with empty lines should be handled correctly."""
        content = """#EXTM3U

#EXTINF:-1 tvg-id="channel1",Channel 1

http://example.com/stream1

"""
        temp_file = self.create_temp_m3u_file(content)

        try:
            channels = parse_m3u(temp_file, source="test_source")
            assert len(channels) == 1
            assert channels[0].tvg_id == "channel1"
        finally:
            os.unlink(temp_file)

    def test_stream_url_without_extinf_warning(self):
        """Stream URL without preceding EXTINF should log warning."""
        content = """#EXTM3U
http://example.com/orphan_stream
#EXTINF:-1 tvg-id="channel1",Channel 1
http://example.com/stream1
"""
        temp_file = self.create_temp_m3u_file(content)

        try:
            with patch("ingest.m3u_parser.logger") as mock_logger:
                channels = parse_m3u(temp_file, source="test_source")

                # Should only parse the channel with EXTINF
                assert len(channels) == 1
                assert channels[0].tvg_id == "channel1"

                # Should log warning about orphan stream
                mock_logger.warning.assert_called()
                warning_calls = [
                    call
                    for call in mock_logger.warning.call_args_list
                    if "Found stream URL without EXTINF" in str(call)
                ]
                assert len(warning_calls) > 0
        finally:
            os.unlink(temp_file)

    def test_channel_without_stream_url_skipped(self):
        """Channel without stream URL should be skipped."""
        content = """#EXTM3U
#EXTINF:-1 tvg-id="channel1",Channel 1
#EXTINF:-1 tvg-id="channel2",Channel 2
http://example.com/stream2
"""
        temp_file = self.create_temp_m3u_file(content)

        try:
            channels = parse_m3u(temp_file, source="test_source")

            # Only channel2 should be parsed (has stream URL)
            assert len(channels) == 1
            assert channels[0].tvg_id == "channel2"
        finally:
            os.unlink(temp_file)

    def test_unknown_tags_tracked(self):
        """Unknown M3U tags should be tracked in validation results."""
        content = """#EXTM3U
#EXT-X-CUSTOM-TAG:some_value
#EXTINF:-1 tvg-id="channel1",Channel 1
http://example.com/stream1
#EXT-X-ANOTHER-TAG:another_value
"""
        temp_file = self.create_temp_m3u_file(content)

        try:
            # Reset validation results before test
            from ingest.m3u_parser import validation_results

            validation_results.unhandled_tags.clear()

            channels = parse_m3u(temp_file, source="test_source")

            assert len(channels) == 1
            # Check that unknown tags were tracked
            assert "#EXT-X-CUSTOM-TAG" in validation_results.unhandled_tags
            assert "#EXT-X-ANOTHER-TAG" in validation_results.unhandled_tags
        finally:
            os.unlink(temp_file)

    def test_file_not_found_raises_exception(self):
        """Non-existent file should raise HTTPException."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            parse_m3u("/non/existent/file.m3u", source="test_source")

        assert exc_info.value.status_code == 500
        assert "Error parsing M3U file" in str(exc_info.value.detail)

    @patch("ingest.m3u_parser.IngestTaskManager")
    def test_task_progress_updates(self, mock_task_manager):
        """Task progress should be updated when task_id provided."""
        content = """#EXTM3U
#EXTINF:-1 tvg-id="channel1",Channel 1
http://example.com/stream1
"""
        temp_file = self.create_temp_m3u_file(content)

        try:
            channels = parse_m3u(temp_file, source="test_source", task_id="task123")

            # Verify task progress was updated
            mock_task_manager.update_step_progress.assert_called_once_with(
                "task123", 2, "Parsing", 0
            )
        finally:
            os.unlink(temp_file)

    def test_default_source_parameter(self):
        """Default source parameter should be 'm3u'."""
        content = """#EXTM3U
#EXTINF:-1 tvg-id="channel1",Channel 1
http://example.com/stream1
"""
        temp_file = self.create_temp_m3u_file(content)

        try:
            channels = parse_m3u(temp_file)  # No source parameter

            assert len(channels) == 1
            assert channels[0].source == "m3u"
        finally:
            os.unlink(temp_file)


class TestM3uValidationResults:
    """Atomic tests for M3uValidationResults class."""

    def test_initialization(self):
        """M3uValidationResults should initialize with empty collections."""
        results = M3uValidationResults()

        assert len(results.unhandled_tags) == 0
        assert len(results.unhandled_extinf_keys) == 0
        assert len(results.channels_without_urls) == 0

    def test_log_results_with_data(self):
        """log_results should log all validation issues."""
        results = M3uValidationResults()
        results.unhandled_tags["#CUSTOM-TAG"] = 3
        results.unhandled_extinf_keys["custom-attr"] = 2
        results.channels_without_urls.append("Channel Without URL")

        with patch("ingest.m3u_parser.logger") as mock_logger:
            results.log_results(context="test_context")

            # Verify logging calls were made
            assert mock_logger.warning.call_count >= 3  # At least one for each category

    def test_log_results_empty(self):
        """log_results with empty data should not log warnings."""
        results = M3uValidationResults()

        with patch("ingest.m3u_parser.logger") as mock_logger:
            results.log_results()

            # Should not log any warnings for empty results
            assert mock_logger.warning.call_count == 0


class TestConstants:
    """Tests for module constants and configuration."""

    def test_expected_m3u_tags_contains_required_tags(self):
        """EXPECTED_M3U_TAGS should contain standard M3U tags."""
        assert "#EXTM3U" in EXPECTED_M3U_TAGS
        assert "#EXTINF" in EXPECTED_M3U_TAGS
        assert "#EXT-X-SESSION-DATA" in EXPECTED_M3U_TAGS

    def test_expected_extinf_keys_contains_standard_keys(self):
        """EXPECTED_EXTINF_KEYS should contain standard EXTINF attributes."""
        expected_keys = {"tvg-id", "tvg-name", "tvg-logo", "group-title", "timeshift"}
        assert expected_keys.issubset(EXPECTED_EXTINF_KEYS)


# Integration test fixtures for more complex scenarios
@pytest.fixture
def sample_m3u_content():
    """Fixture providing sample M3U content for integration tests."""
    return """#EXTM3U
#EXT-X-SESSION-DATA:DATA-ID="com.example.session"
#EXTINF:-1 tvg-id="cnn.us" tvg-name="CNN" tvg-logo="http://example.com/cnn.png" group-title="News",CNN
http://example.com/cnn/stream.m3u8
#EXTINF:-1 tvg-id="espn.us" tvg-name="ESPN" tvg-logo="http://example.com/espn.png" group-title="Sports",ESPN
http://example.com/espn/stream
#EXTINF:-1 tvg-id="movie1" tvg-name="Movie Channel" group-title="Movies",Movie Channel
http://example.com/movies/movie.mp4
#EXTINF:-1,Channel Without Attributes
http://example.com/basic/stream
"""


class TestIntegrationScenarios:
    """Integration tests for complex M3U parsing scenarios."""

    def test_complete_m3u_parsing_workflow(self, sample_m3u_content):
        """Test complete M3U parsing workflow with various channel types."""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".m3u", delete=False)
        temp_file.write(sample_m3u_content)
        temp_file.close()

        try:
            channels = parse_m3u(temp_file.name, source="integration_test")

            assert len(channels) == 4

            # Test CNN (complete attributes)
            cnn = next(ch for ch in channels if ch.tvg_id == "cnn.us")
            assert cnn.name == "CNN"
            assert cnn.logo_url == "http://example.com/cnn.png"
            assert cnn.group == "News"
            assert cnn.stream_mode == "live"

            # Test Movie Channel (on-demand detection)
            movie = next(ch for ch in channels if ch.tvg_id == "movie1")
            assert movie.stream_mode == "on_demand"

            # Test channel without attributes
            basic = next(
                ch for ch in channels if ch.name == "Channel Without Attributes"
            )
            assert basic.tvg_id == "Channel Without Attributes"  # Uses name as fallback
            assert basic.logo_url is None
            assert basic.group is None

        finally:
            os.unlink(temp_file.name)
