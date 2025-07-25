"""Tests for parse_extinf_line function following atomic design principles.

This module focuses exclusively on testing EXTINF line parsing logic.
Each test validates one specific parsing scenario or edge case.
"""

import pytest

from ingest.m3u_parser import parse_extinf_line


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

    def test_unexpected_text_before_extinf(self):
        """#EXTINF line with text before it should parse correctly"""
        line = "Extra Text #EXTINF:-1 tvg-id=channel1 group-title=GroupName,Channel"

        attrs, name = parse_extinf_line(line)

        assert attrs == {"tvg-id": "channel1", "group-title": "GroupName"}
        assert name == "Channel"
