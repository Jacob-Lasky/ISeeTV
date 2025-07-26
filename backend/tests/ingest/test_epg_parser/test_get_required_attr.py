"""Tests for get_required_attr function following atomic design principles.

This module focuses exclusively on testing required attribute extraction logic.
Each test validates one specific extraction scenario or edge case.
"""

import pytest
from unittest.mock import patch, MagicMock
from lxml import etree

from ingest.epg_parser import get_required_attr


class TestGetRequiredAttr:
    """Atomic tests for get_required_attr function."""

    def test_get_required_attr_success(self):
        """Should return attribute value when attribute exists and has content."""
        xml = '<programme channel="ch1" start="123456"></programme>'
        elem = etree.fromstring(xml)

        result = get_required_attr(elem, "channel")

        assert result == "ch1"

    def test_get_required_attr_with_whitespace(self):
        """Should strip whitespace from attribute value."""
        xml = '<programme channel="  ch1  " start="123456"></programme>'
        elem = etree.fromstring(xml)

        result = get_required_attr(elem, "channel")

        assert result == "ch1"

    def test_get_required_attr_missing_attribute(self):
        """Should raise ValueError when required attribute is missing."""
        xml = '<programme start="123456"></programme>'
        elem = etree.fromstring(xml)

        with pytest.raises(ValueError) as exc_info:
            get_required_attr(elem, "channel")

        assert "Missing required attribute 'channel'" in str(exc_info.value)

    def test_get_required_attr_empty_attribute(self):
        """Should raise ValueError when attribute exists but is empty."""
        xml = '<programme channel="" start="123456"></programme>'
        elem = etree.fromstring(xml)

        with pytest.raises(ValueError) as exc_info:
            get_required_attr(elem, "channel")

        assert "Missing required attribute 'channel'" in str(exc_info.value)

    def test_get_required_attr_whitespace_only(self):
        """Should raise ValueError when attribute contains only whitespace."""
        xml = '<programme channel="   " start="123456"></programme>'
        elem = etree.fromstring(xml)

        with pytest.raises(ValueError) as exc_info:
            get_required_attr(elem, "channel")

        assert "Missing required attribute 'channel'" in str(exc_info.value)

    def test_get_required_attr_with_context(self):
        """Should include context in error message when provided."""
        xml = '<programme start="123456"></programme>'
        elem = etree.fromstring(xml)

        with pytest.raises(ValueError) as exc_info:
            get_required_attr(elem, "channel", context="prog1")

        error_msg = str(exc_info.value)
        assert "Missing required attribute 'channel'" in error_msg
        assert "Context: prog1" in error_msg

    def test_get_required_attr_with_line_number(self):
        """Should include line number in error message when available."""
        xml = """<programme 
                    start="123456">
                 </programme>"""
        elem = etree.fromstring(xml)

        with pytest.raises(ValueError) as exc_info:
            get_required_attr(elem, "channel", context="test")

        error_msg = str(exc_info.value)
        assert "at line" in error_msg
        assert "Context: test" in error_msg

    def test_get_required_attr_no_line_number(self):
        """Should handle missing line number gracefully."""
        xml = '<programme start="123456"></programme>'
        elem = etree.fromstring(xml)

        with pytest.raises(ValueError) as exc_info:
            get_required_attr(elem, "channel")

        error_msg = str(exc_info.value)
        assert "Missing required attribute 'channel' at line 1" in error_msg

    def test_get_required_attr_unicode_content(self):
        """Should handle unicode attribute values correctly."""
        xml = '<programme channel="频道1"></programme>'
        elem = etree.fromstring(xml)

        result = get_required_attr(elem, "channel")

        assert result == "频道1"

    def test_get_required_attr_special_characters(self):
        """Should handle special characters in attribute values."""
        xml = '<programme channel="ch-1_test.channel@domain.com"></programme>'
        elem = etree.fromstring(xml)

        result = get_required_attr(elem, "channel")

        assert result == "ch-1_test.channel@domain.com"

    def test_get_required_attr_numeric_content(self):
        """Should handle numeric attribute values as strings."""
        xml = '<programme start_timestamp="1751953500"></programme>'
        elem = etree.fromstring(xml)

        result = get_required_attr(elem, "start_timestamp")

        assert result == "1751953500"
        assert isinstance(result, str)

    def test_get_required_attr_boolean_like_content(self):
        """Should handle boolean-like attribute values as strings."""
        xml = '<programme active="true"></programme>'
        elem = etree.fromstring(xml)

        result = get_required_attr(elem, "active")

        assert result == "true"
        assert isinstance(result, str)

    @pytest.mark.parametrize(
        "attr_name",
        ["channel", "start", "stop", "start_timestamp", "stop_timestamp", "program-id"],
    )
    def test_get_required_attr_various_attributes(self, attr_name):
        """Should work with various common EPG attribute names."""
        xml = f'<programme {attr_name}="test_value"></programme>'
        elem = etree.fromstring(xml)

        result = get_required_attr(elem, attr_name)

        assert result == "test_value"

    def test_get_required_attr_case_sensitive(self):
        """Should be case-sensitive for attribute names."""
        xml = '<programme Channel="ch1"></programme>'  # Wrong case
        elem = etree.fromstring(xml)

        with pytest.raises(ValueError) as exc_info:
            get_required_attr(elem, "channel")  # Correct case

        assert "Missing required attribute 'channel'" in str(exc_info.value)

    def test_get_required_attr_namespace_attributes(self):
        """Should handle namespaced attributes correctly."""
        xml = '<programme xmlns:custom="http://example.com" custom:channel="ch1"></programme>'
        elem = etree.fromstring(xml)

        # Test accessing namespaced attribute
        result = get_required_attr(elem, "{http://example.com}channel")

        assert result == "ch1"

    def test_get_required_attr_url_values(self):
        """Should handle URL values in attributes correctly."""
        xml = '<icon src="https://example.com/icon.png?param=value&amp;other=test"></icon>'
        elem = etree.fromstring(xml)

        result = get_required_attr(elem, "src")

        assert result == "https://example.com/icon.png?param=value&other=test"

    def test_get_required_attr_multiline_values(self):
        """Should handle multiline attribute values correctly."""
        xml = """<programme title="Line 1
Line 2
Line 3"></programme>"""
        elem = etree.fromstring(xml)

        result = get_required_attr(elem, "title")

        # Should preserve the multiline content but strip outer whitespace
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
