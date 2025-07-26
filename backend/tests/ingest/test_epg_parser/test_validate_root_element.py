"""Tests for validate_root_element function following atomic design principles.

This module focuses exclusively on testing root element validation logic.
Each test validates one specific validation scenario or edge case.
"""

import pytest
from unittest.mock import patch, MagicMock
from lxml import etree

from ingest.epg_parser import validate_root_element, validation_results


class TestValidateRootElement:
    """Atomic tests for validate_root_element function."""

    def setup_method(self):
        """Reset validation results before each test."""
        validation_results.unexpected_root_attrs.clear()

    def test_valid_root_element_no_attributes(self):
        """Root element with no attributes should validate without issues."""
        xml = "<tv></tv>"
        root = etree.fromstring(xml)

        validate_root_element(root)

        assert len(validation_results.unexpected_root_attrs) == 0

    def test_valid_root_element_with_expected_attributes(self):
        """Root element with expected attributes should validate without issues."""
        xml = (
            '<tv generator-info-name="test" generator-info-url="http://test.com"></tv>'
        )
        root = etree.fromstring(xml)

        validate_root_element(root)

        assert len(validation_results.unexpected_root_attrs) == 0

    def test_root_element_with_unexpected_attribute(self):
        """Root element with unexpected attribute should record validation issue."""
        xml = '<tv unknown-attr="value"></tv>'
        root = etree.fromstring(xml)

        validate_root_element(root)

        # Check that the global validation_results was updated
        from ingest import epg_parser

        assert "unknown-attr" in epg_parser.validation_results.unexpected_root_attrs

    def test_root_element_with_multiple_unexpected_attributes(self):
        """Root element with multiple unexpected attributes should record all issues."""
        xml = (
            '<tv unknown1="value1" unknown2="value2" generator-info-name="valid"></tv>'
        )
        root = etree.fromstring(xml)

        validate_root_element(root)

        # Check that the global validation_results was updated
        from ingest import epg_parser

        assert "unknown1" in epg_parser.validation_results.unexpected_root_attrs
        assert "unknown2" in epg_parser.validation_results.unexpected_root_attrs
        assert "generator-info-name" not in validation_results.unexpected_root_attrs

    def test_root_element_with_mixed_attributes(self):
        """Root element with mix of expected and unexpected attributes should only record unexpected ones."""
        xml = """<tv 
                    generator-info-name="IPTV" 
                    generator-info-url="http://example.com"
                    source-info-name="Provider"
                    source-info-url="http://provider.com"
                    source-data-url="http://data.com"
                    unknown-attr="bad"
                    another-bad="also-bad">
                 </tv>"""
        root = etree.fromstring(xml)

        validate_root_element(root)

        # Check that the global validation_results was updated
        from ingest import epg_parser

        # Should only contain unexpected attributes
        assert "unknown-attr" in epg_parser.validation_results.unexpected_root_attrs
        assert "another-bad" in epg_parser.validation_results.unexpected_root_attrs
        assert len(epg_parser.validation_results.unexpected_root_attrs) == 2

    def test_namespace_attributes(self):
        """Root element with namespace attributes should be handled correctly."""
        xml = '<tv xmlns:custom="http://example.com" custom:attr="value"></tv>'
        root = etree.fromstring(xml)

        validate_root_element(root)

        # Namespace declarations and namespaced attributes should be recorded as unexpected
        # (unless they're in the expected list)
        assert len(validation_results.unexpected_root_attrs) > 0

    def test_empty_attribute_values(self):
        """Root element with empty attribute values should still be recorded as unexpected if not in expected list."""
        xml = '<tv unknown-attr=""></tv>'
        root = etree.fromstring(xml)

        validate_root_element(root)

        # Check that the global validation_results was updated
        from ingest import epg_parser

        assert "unknown-attr" in epg_parser.validation_results.unexpected_root_attrs

    def test_whitespace_attribute_values(self):
        """Root element with whitespace-only attribute values should still be validated."""
        xml = '<tv unknown-attr="   "></tv>'
        root = etree.fromstring(xml)

        validate_root_element(root)

        # Check that the global validation_results was updated
        from ingest import epg_parser

        assert "unknown-attr" in epg_parser.validation_results.unexpected_root_attrs

    def test_unicode_attribute_names(self):
        """Root element with unicode attribute names should be handled correctly."""
        xml = '<tv générator-info="test"></tv>'
        root = etree.fromstring(xml)

        validate_root_element(root)

        # Check that the global validation_results was updated
        from ingest import epg_parser

        assert "générator-info" in epg_parser.validation_results.unexpected_root_attrs

    def test_case_sensitive_attribute_validation(self):
        """Attribute validation should be case-sensitive."""
        xml = '<tv Generator-Info-Name="test"></tv>'  # Wrong case
        root = etree.fromstring(xml)

        validate_root_element(root)

        # Check that the global validation_results was updated
        from ingest import epg_parser

        assert (
            "Generator-Info-Name" in epg_parser.validation_results.unexpected_root_attrs
        )

    def test_namespace_attributes(self):
        """Root element with namespace attributes should be handled correctly."""
        xml = '<tv xmlns:custom="http://example.com" custom:attr="value"></tv>'
        root = etree.fromstring(xml)

        validate_root_element(root)

        # Namespace declarations and namespaced attributes should be recorded as unexpected
        # (unless they're in the expected list)
        assert len(validation_results.unexpected_root_attrs) > 0
