"""Tests for validate_root_tags function following atomic design principles.

This module focuses exclusively on testing EPG root tag validation logic.
Each test validates one specific validation scenario or edge case.
"""

import pytest
from unittest.mock import patch, MagicMock
from lxml import etree

from ingest.epg_parser import validate_root_tags


class TestValidateRootTags:
    """Atomic tests for validate_root_tags function."""

    @patch('ingest.epg_parser.validation_results')
    def test_correct_root_tags_only(self, mock_validation_results):
        """Should not record any unexpected tags when only correct tags (channel, programme) are present."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel 1</display-name>
            </channel>
            <programme channel="ch1" start="20240101000000" stop="20240101010000">
                <title>Test Program</title>
                <desc>Program description</desc>
            </programme>
            <programme channel="ch1" start="20240101010000" stop="20240101020000">
                <title>Another Program</title>
            </programme>
        </tv>"""
        root = etree.fromstring(xml_content.encode("utf-8"))

        validate_root_tags(root)

        # Should not increment unexpected_root_tags for valid tags
        mock_validation_results.unexpected_root_tags.__getitem__.assert_not_called()

    @patch('ingest.epg_parser.validation_results')
    def test_incorrect_root_tags_recorded(self, mock_validation_results):
        """Should record unexpected/incorrect root tags in validation results."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel 1</display-name>
            </channel>
            <programme channel="ch1" start="20240101000000" stop="20240101010000">
                <title>Test Program</title>
            </programme>
            <unexpected-tag>This should be recorded</unexpected-tag>
            <invalid-element>Another invalid tag</invalid-element>
        </tv>"""
        root = etree.fromstring(xml_content.encode("utf-8"))

        validate_root_tags(root)

        # Should increment unexpected_root_tags for invalid tags
        mock_validation_results.unexpected_root_tags.__getitem__.assert_any_call("unexpected-tag")
        mock_validation_results.unexpected_root_tags.__getitem__.assert_any_call("invalid-element")
        # Should increment counters for unexpected tags
        assert mock_validation_results.unexpected_root_tags.__getitem__.return_value.__iadd__.call_count == 2

    @patch('ingest.epg_parser.validation_results')
    def test_mixed_correct_and_incorrect_tags(self, mock_validation_results):
        """Should only record incorrect tags while ignoring correct ones."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel 1</display-name>
            </channel>
            <wrong-tag>This is wrong</wrong-tag>
            <programme channel="ch1" start="20240101000000" stop="20240101010000">
                <title>Test Program</title>
            </programme>
            <another-wrong>Also wrong</another-wrong>
            <channel id="ch2">
                <display-name>Channel 2</display-name>
            </channel>
        </tv>"""
        root = etree.fromstring(xml_content.encode("utf-8"))

        validate_root_tags(root)

        # Should only record the incorrect tags
        mock_validation_results.unexpected_root_tags.__getitem__.assert_any_call("wrong-tag")
        mock_validation_results.unexpected_root_tags.__getitem__.assert_any_call("another-wrong")
        # Should increment counters for unexpected tags only
        assert mock_validation_results.unexpected_root_tags.__getitem__.return_value.__iadd__.call_count == 2

    @patch('ingest.epg_parser.validation_results')
    def test_multiple_same_incorrect_tags(self, mock_validation_results):
        """Should count multiple occurrences of the same incorrect tag."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel 1</display-name>
            </channel>
            <wrong-tag>First occurrence</wrong-tag>
            <wrong-tag>Second occurrence</wrong-tag>
            <wrong-tag>Third occurrence</wrong-tag>
        </tv>"""
        root = etree.fromstring(xml_content.encode("utf-8"))

        validate_root_tags(root)

        # Should record the same incorrect tag multiple times
        assert mock_validation_results.unexpected_root_tags.__getitem__.call_count == 3
        mock_validation_results.unexpected_root_tags.__getitem__.assert_called_with("wrong-tag")
        # Should increment counter for each occurrence
        assert mock_validation_results.unexpected_root_tags.__getitem__.return_value.__iadd__.call_count == 3

    @patch('ingest.epg_parser.validation_results')
    def test_empty_root_element(self, mock_validation_results):
        """Should handle empty root element without errors."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv></tv>"""
        root = etree.fromstring(xml_content.encode("utf-8"))

        validate_root_tags(root)

        # Should not record any unexpected tags for empty root
        mock_validation_results.unexpected_root_tags.__getitem__.assert_not_called()

    @patch('ingest.epg_parser.validation_results')
    def test_namespace_tags_as_incorrect(self, mock_validation_results):
        """Should treat namespaced tags as incorrect/unexpected."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel 1</display-name>
            </channel>
            <ns:custom-tag xmlns:ns="http://example.com">Namespaced content</ns:custom-tag>
        </tv>"""
        root = etree.fromstring(xml_content.encode("utf-8"))

        validate_root_tags(root)

        # Should record the namespaced tag as unexpected
        # The tag name will include the namespace prefix
        call_args = mock_validation_results.unexpected_root_tags.__getitem__.call_args_list
        assert len(call_args) == 1
        called_tag = call_args[0][0][0]
        assert "custom-tag" in called_tag  # Should contain the tag name

    def test_validate_root_tags_basic_functionality(self):
        """Basic test to ensure function runs without errors on valid XML."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="1735689600" stop_timestamp="1735693200">
                <title>Test Program</title>
                <desc>Program description</desc>
            </programme>
            <programme channel="ch2" start_timestamp="1735693200" stop_timestamp="1735696800">
                <title>Another Program</title>
            </programme>
        </tv>"""
        root = etree.fromstring(xml_content.encode("utf-8"))

        validate_root_tags(root)

        assert root.tag == "tv"