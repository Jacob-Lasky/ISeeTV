"""Tests for validate_channel_element function following atomic design principles.

This module focuses exclusively on testing channel element validation logic.
Each test validates one specific validation scenario or edge case.
"""

import pytest
from unittest.mock import patch, MagicMock
from lxml import etree

from ingest.epg_parser import validate_channel_element, validation_results


class TestValidateChannelElement:
    """Atomic tests for validate_channel_element function."""

    def setup_method(self):
        """Reset validation results before each test."""
        validation_results.unexpected_channel_attrs.clear()
        validation_results.unexpected_channel_tags.clear()

    def test_valid_channel_element_minimal(self):
        """Channel element with minimal valid structure should validate correctly."""
        xml = '<channel id="channel1"></channel>'
        channel = etree.fromstring(xml)

        channel_id = validate_channel_element(channel)

        assert channel_id == "channel1"
        assert len(validation_results.unexpected_channel_attrs) == 0
        assert len(validation_results.unexpected_channel_tags) == 0

    def test_channel_element_missing_id(self):
        """Channel element without id attribute should return 'Unknown'."""
        xml = "<channel></channel>"
        channel = etree.fromstring(xml)

        channel_id = validate_channel_element(channel)

        assert channel_id == "Unknown"

    def test_channel_element_empty_id(self):
        """Channel element with empty id should return empty string."""
        xml = '<channel id=""></channel>'
        channel = etree.fromstring(xml)

        channel_id = validate_channel_element(channel)

        assert channel_id == ""

    def test_channel_element_with_expected_children(self):
        """Channel element with expected child tags should validate without issues."""
        xml = """<channel id="ch1">
                    <display-name>Channel 1</display-name>
                    <icon src="http://icon.png"/>
                    <url>http://channel.com</url>
                 </channel>"""
        channel = etree.fromstring(xml)

        channel_id = validate_channel_element(channel)

        assert channel_id == "ch1"
        assert len(validation_results.unexpected_channel_tags) == 0

    def test_channel_element_with_unexpected_child_tags(self):
        """Channel element with unexpected child tags should record validation issues."""
        xml = """<channel id="ch1">
                    <display-name>Channel 1</display-name>
                    <unknown-tag>Bad content</unknown-tag>
                    <another-bad>Also bad</another-bad>
                 </channel>"""
        channel = etree.fromstring(xml)

        channel_id = validate_channel_element(channel)

        assert channel_id == "ch1"
        assert validation_results.unexpected_channel_tags["unknown-tag"] == 1
        assert validation_results.unexpected_channel_tags["another-bad"] == 1

    def test_channel_element_with_unexpected_attributes(self):
        """Channel element with unexpected attributes should record validation issues."""
        xml = '<channel id="ch1" unknown-attr="bad" another-bad="also-bad"></channel>'
        channel = etree.fromstring(xml)

        channel_id = validate_channel_element(channel)

        assert channel_id == "ch1"
        assert "unknown-attr" in validation_results.unexpected_channel_attrs["ch1"]
        assert "another-bad" in validation_results.unexpected_channel_attrs["ch1"]
        assert "id" not in validation_results.unexpected_channel_attrs["ch1"]

    def test_multiple_channels_separate_validation(self):
        """Multiple channel validations should track issues separately by channel ID."""
        xml1 = '<channel id="ch1" bad-attr1="value"></channel>'
        xml2 = '<channel id="ch2" bad-attr2="value"></channel>'

        channel1 = etree.fromstring(xml1)
        channel2 = etree.fromstring(xml2)

        id1 = validate_channel_element(channel1)
        id2 = validate_channel_element(channel2)

        assert id1 == "ch1"
        assert id2 == "ch2"
        assert "bad-attr1" in validation_results.unexpected_channel_attrs["ch1"]
        assert "bad-attr2" in validation_results.unexpected_channel_attrs["ch2"]
        assert "bad-attr1" not in validation_results.unexpected_channel_attrs["ch2"]
        assert "bad-attr2" not in validation_results.unexpected_channel_attrs["ch1"]

    def test_channel_with_duplicate_unexpected_tags(self):
        """Channel with duplicate unexpected tags should accumulate counts."""
        xml = """<channel id="ch1">
                    <unknown-tag>First</unknown-tag>
                    <unknown-tag>Second</unknown-tag>
                    <different-bad>Other</different-bad>
                 </channel>"""
        channel = etree.fromstring(xml)

        validate_channel_element(channel)

        assert validation_results.unexpected_channel_tags["unknown-tag"] == 2
        assert validation_results.unexpected_channel_tags["different-bad"] == 1

    def test_channel_with_mixed_valid_invalid_content(self):
        """Channel with mix of valid and invalid content should only record invalid items."""
        xml = """<channel id="ch1" valid-attr="ok" bad-attr="bad">
                    <display-name>Valid</display-name>
                    <icon src="valid.png"/>
                    <bad-tag>Invalid</bad-tag>
                 </channel>"""
        channel = etree.fromstring(xml)

        channel_id = validate_channel_element(channel)

        assert channel_id == "ch1"
        # Should only record the bad attribute (assuming valid-attr is expected)
        assert "bad-attr" in validation_results.unexpected_channel_attrs["ch1"]
        # Should only record the bad tag
        assert validation_results.unexpected_channel_tags["bad-tag"] == 1

    def test_channel_with_whitespace_id(self):
        """Channel with whitespace in id should preserve the whitespace."""
        xml = '<channel id="  ch1  "></channel>'
        channel = etree.fromstring(xml)

        channel_id = validate_channel_element(channel)

        assert channel_id == "  ch1  "

    def test_channel_with_unicode_id(self):
        """Channel with unicode characters in id should be handled correctly."""
        xml = '<channel id="频道1"></channel>'
        channel = etree.fromstring(xml)

        channel_id = validate_channel_element(channel)

        assert channel_id == "频道1"

    def test_channel_with_special_characters_id(self):
        """Channel with special characters in id should be handled correctly."""
        xml = '<channel id="ch-1_test.channel@domain.com"></channel>'
        channel = etree.fromstring(xml)

        channel_id = validate_channel_element(channel)

        assert channel_id == "ch-1_test.channel@domain.com"
