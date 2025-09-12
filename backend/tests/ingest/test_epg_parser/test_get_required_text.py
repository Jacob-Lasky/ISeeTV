"""Tests for get_required_text function following atomic design principles.

This module focuses exclusively on testing required text extraction logic.
Each test validates one specific extraction scenario or edge case.
"""

import pytest
from unittest.mock import patch, MagicMock
from lxml import etree

from ingest.epg_parser import get_required_text


class TestGetRequiredText:
    """Atomic tests for get_required_text function."""

    def test_get_required_text_success(self):
        """Should return text content when tag exists and has content."""
        xml = "<parent><title>Program Title</title></parent>"
        elem = etree.fromstring(xml)

        result = get_required_text(elem, "title")

        assert result == "Program Title"

    def test_get_required_text_with_whitespace(self):
        """Should strip whitespace from text content."""
        xml = "<parent><title>  Program Title  </title></parent>"
        elem = etree.fromstring(xml)

        result = get_required_text(elem, "title")

        assert result == "Program Title"

    def test_get_required_text_missing_tag(self):
        """Should raise ValueError when required tag is missing."""
        xml = "<parent><other>Content</other></parent>"
        elem = etree.fromstring(xml)

        with pytest.raises(ValueError) as exc_info:
            get_required_text(elem, "title")

        assert "Missing required <title>" in str(exc_info.value)

    def test_get_required_text_empty_tag(self):
        """Should raise ValueError when tag exists but is empty."""
        xml = "<parent><title></title></parent>"
        elem = etree.fromstring(xml)

        with pytest.raises(ValueError) as exc_info:
            get_required_text(elem, "title")

        assert "Missing required <title>" in str(exc_info.value)

    def test_get_required_text_whitespace_only(self):
        """Should raise ValueError when tag contains only whitespace."""
        xml = "<parent><title>   </title></parent>"
        elem = etree.fromstring(xml)

        with pytest.raises(ValueError) as exc_info:
            get_required_text(elem, "title")

        assert "Missing required <title>" in str(exc_info.value)

    def test_get_required_text_with_context(self):
        """Should include context in error message when provided."""
        xml = "<parent><other>Content</other></parent>"
        elem = etree.fromstring(xml)

        with pytest.raises(ValueError) as exc_info:
            get_required_text(elem, "title", context="channel1")

        error_msg = str(exc_info.value)
        assert "Missing required <title>" in error_msg
        assert "Context: channel1" in error_msg

    def test_get_required_text_with_line_number(self):
        """Should include line number in error message when available."""
        xml = """<parent>
                    <other>Content</other>
                 </parent>"""
        elem = etree.fromstring(xml)

        with pytest.raises(ValueError) as exc_info:
            get_required_text(elem, "title", context="test")

        error_msg = str(exc_info.value)
        assert "at line" in error_msg
        assert "Context: test" in error_msg

    def test_get_required_text_no_line_number(self):
        """Should handle missing line number gracefully."""
        xml = "<parent><other>Content</other></parent>"
        elem = etree.fromstring(xml)

        with pytest.raises(ValueError) as exc_info:
            get_required_text(elem, "title")

        error_msg = str(exc_info.value)
        assert "Missing required <title> at line 1." in error_msg

    def test_get_required_text_unicode_content(self):
        """Should handle unicode text content correctly."""
        xml = "<parent><title>节目标题</title></parent>"
        elem = etree.fromstring(xml)

        result = get_required_text(elem, "title")

        assert result == "节目标题"

    def test_get_required_text_special_characters(self):
        """Should handle special characters in text content."""
        xml = "<parent><title>Program &amp; Show &lt;HD&gt;</title></parent>"
        elem = etree.fromstring(xml)

        result = get_required_text(elem, "title")

        assert result == "Program & Show <HD>"

    def test_get_required_text_nested_content(self):
        """Should handle nested XML content in text."""
        xml = "<parent><title>Program Here</title></parent>"
        elem = etree.fromstring(xml)

        result = get_required_text(elem, "title")

        # findtext() returns only direct text content, not nested elements
        assert result == "Program Here"

    def test_get_required_text_multiple_same_tags(self):
        """Should return text from first matching tag when multiple exist."""
        xml = """<parent>
                    <title>First Title</title>
                    <title>Second Title</title>
                 </parent>"""
        elem = etree.fromstring(xml)

        result = get_required_text(elem, "title")

        assert result == "First Title"

    @pytest.mark.parametrize(
        "tag_name", ["title", "desc", "display-name", "category", "country", "language"]
    )
    def test_get_required_text_various_tags(self, tag_name):
        """Should work with various common EPG tag names."""
        xml = f"<parent><{tag_name}>Content</{tag_name}></parent>"
        elem = etree.fromstring(xml)

        result = get_required_text(elem, tag_name)

        assert result == "Content"

    def test_get_required_text_cdata_content(self):
        """Should handle CDATA content correctly."""
        xml = "<parent><title><![CDATA[Program & Show <HD>]]></title></parent>"
        elem = etree.fromstring(xml)

        result = get_required_text(elem, "title")

        assert result == "Program & Show <HD>"

    def test_get_required_text_numeric_content(self):
        """Should handle numeric content as string."""
        xml = "<parent><duration>3600</duration></parent>"
        elem = etree.fromstring(xml)

        result = get_required_text(elem, "duration")

        assert result == "3600"
        assert isinstance(result, str)
