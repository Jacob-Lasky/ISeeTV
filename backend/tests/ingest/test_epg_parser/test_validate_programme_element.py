"""Tests for validate_programme_element function following atomic design principles.

This module focuses exclusively on testing programme element validation logic.
Each test validates one specific validation scenario or edge case.
"""

import pytest
from unittest.mock import patch, MagicMock
from lxml import etree

from ingest.epg_parser import validate_programme_element, ValidationResults


class TestValidateProgrammeElement:
    """Atomic tests for validate_programme_element function."""

    def test_programme_element_with_program_id(self):
        """Programme element with program-id attribute should return that ID."""
        validation_results = ValidationResults()
        xml = '<programme program-id="prog123" channel="ch1"></programme>'
        programme = etree.fromstring(xml)

        programme_id = validate_programme_element(programme, validation_results)

        assert programme_id == "prog123"

    def test_programme_element_with_channel_id_fallback(self):
        """Programme element without program-id should fallback to channel attribute."""
        validation_results = ValidationResults()
        xml = '<programme channel="ch1" start="123456"></programme>'
        programme = etree.fromstring(xml)

        programme_id = validate_programme_element(programme, validation_results)

        assert programme_id == "ch1"

    def test_programme_element_missing_both_ids(self):
        """Programme element without program-id or channel should return 'Unknown'."""
        validation_results = ValidationResults()
        xml = '<programme start="123456"></programme>'
        programme = etree.fromstring(xml)

        programme_id = validate_programme_element(programme, validation_results)

        assert programme_id == "Unknown"

    def test_programme_element_empty_program_id(self):
        """Programme element with empty program-id should fallback to channel."""
        validation_results = ValidationResults()
        xml = '<programme program-id="" channel="ch1"></programme>'
        programme = etree.fromstring(xml)

        programme_id = validate_programme_element(programme, validation_results)

        assert programme_id == "ch1"

    def test_programme_element_empty_both_ids(self):
        """Programme element with empty program-id and channel should return 'Unknown'."""
        validation_results = ValidationResults()
        xml = '<programme program-id="" channel=""></programme>'
        programme = etree.fromstring(xml)

        programme_id = validate_programme_element(programme, validation_results)

        assert programme_id == "Unknown"

    def test_programme_element_with_expected_children(self):
        """Programme element with expected child tags should validate without issues."""
        validation_results = ValidationResults()
        xml = """<programme program-id="prog1" channel="ch1">
                    <title>Program Title</title>
                    <desc>Program description</desc>
                    <date>20240101</date>
                    <category>News</category>
                 </programme>"""
        programme = etree.fromstring(xml)

        programme_id = validate_programme_element(programme, validation_results)

        assert programme_id == "prog1"
        assert len(validation_results.unexpected_programme_tags) == 2
        assert "title" not in validation_results.unexpected_programme_tags
        assert "desc" not in validation_results.unexpected_programme_tags

    def test_programme_element_with_unexpected_child_tags(self):
        """Programme element with unexpected child tags should record validation issues."""
        validation_results = ValidationResults()
        xml = """<programme program-id="prog1" channel="ch1">
                    <title>Program Title</title>
                    <unknown-tag>Bad content</unknown-tag>
                    <another-bad>Also bad</another-bad>
                 </programme>"""
        programme = etree.fromstring(xml)

        programme_id = validate_programme_element(programme, validation_results)

        assert programme_id == "prog1"
        assert validation_results.unexpected_programme_tags["unknown-tag"] == 1
        assert validation_results.unexpected_programme_tags["another-bad"] == 1

    def test_programme_element_with_unexpected_attributes(self):
        """Programme element with unexpected attributes should record validation issues."""
        validation_results = ValidationResults()
        xml = '<programme channel="ch1" start_timestamp="123456" unknown-attr="bad" another-bad="also-bad"></programme>'
        programme = etree.fromstring(xml)

        programme_id = validate_programme_element(programme, validation_results)

        assert programme_id == "ch1"
        assert "unknown-attr" in validation_results.unexpected_programme_attrs["ch1"]
        assert "another-bad" in validation_results.unexpected_programme_attrs["ch1"]
        assert (
            "start_timestamp" not in validation_results.unexpected_programme_attrs["ch1"]
        )
        assert "channel" not in validation_results.unexpected_programme_attrs["ch1"]

    def test_multiple_programmes_separate_validation(self):
        """Multiple programme validations should track issues separately by programme ID."""
        validation_results = ValidationResults()
        xml1 = '<programme program-id="prog1" bad-attr1="value"></programme>'
        xml2 = '<programme program-id="prog2" bad-attr2="value"></programme>'

        programme1 = etree.fromstring(xml1)
        programme2 = etree.fromstring(xml2)

        id1 = validate_programme_element(programme1, validation_results)
        id2 = validate_programme_element(programme2, validation_results)

        assert id1 == "prog1"
        assert id2 == "prog2"
        assert "bad-attr1" in validation_results.unexpected_programme_attrs["prog1"]
        assert "bad-attr2" in validation_results.unexpected_programme_attrs["prog2"]
        assert "bad-attr1" not in validation_results.unexpected_programme_attrs["prog2"]
        assert "bad-attr2" not in validation_results.unexpected_programme_attrs["prog1"]

    def test_programme_with_duplicate_unexpected_tags(self):
        """Programme with duplicate unexpected tags should accumulate counts."""
        validation_results = ValidationResults()
        xml = """<programme program-id="prog1">
                    <unknown-tag>First</unknown-tag>
                    <unknown-tag>Second</unknown-tag>
                    <different-bad>Other</different-bad>
                 </programme>"""
        programme = etree.fromstring(xml)

        validate_programme_element(programme, validation_results)

        assert validation_results.unexpected_programme_tags["unknown-tag"] == 2
        assert validation_results.unexpected_programme_tags["different-bad"] == 1

    def test_programme_with_mixed_valid_invalid_content(self):
        """Programme with mix of valid and invalid content should only record invalid items."""
        validation_results = ValidationResults()
        xml = """<programme program-id="prog1" channel="ch1" bad-attr="bad">
                    <title>Valid</title>
                    <desc>Valid description</desc>
                    <bad-tag>Invalid</bad-tag>
                 </programme>"""
        programme = etree.fromstring(xml)

        programme_id = validate_programme_element(programme, validation_results)

        assert programme_id == "prog1"
        assert "bad-attr" in validation_results.unexpected_programme_attrs["prog1"]
        assert validation_results.unexpected_programme_tags["bad-tag"] == 1

    def test_programme_with_whitespace_ids(self):
        """Programme with whitespace in IDs should preserve the whitespace."""
        validation_results = ValidationResults()
        xml = '<programme program-id="  prog1  " channel="  ch1  "></programme>'
        programme = etree.fromstring(xml)

        programme_id = validate_programme_element(programme, validation_results)

        assert programme_id == "  prog1  "

    def test_programme_with_unicode_ids(self):
        """Programme with unicode characters in IDs should be handled correctly."""
        validation_results = ValidationResults()
        xml = '<programme program-id="节目1" channel="频道1"></programme>'
        programme = etree.fromstring(xml)

        programme_id = validate_programme_element(programme, validation_results)

        assert programme_id == "节目1"

    def test_programme_with_special_characters_ids(self):
        """Programme with special characters in IDs should be handled correctly."""
        xml = '<programme program-id="prog-1_test.show@domain.com" channel="ch-1"></programme>'
        programme = etree.fromstring(xml)

        programme_id = validate_programme_element(programme)

        assert programme_id == "prog-1_test.show@domain.com"
