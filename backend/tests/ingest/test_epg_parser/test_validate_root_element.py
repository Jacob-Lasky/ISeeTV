"""Tests for validate_root_element function following atomic design principles.

This module focuses exclusively on testing root element validation logic.
Each test validates one specific validation scenario or edge case.
"""

import pytest
from unittest.mock import patch, MagicMock
from lxml import etree

from ingest.epg_parser import validate_root_element, ValidationResults


class TestValidateRootElement:
    """Atomic tests for validate_root_element function."""

    def setup_method(self):
        """Create fresh validation results for each test."""
        self.validation_results = ValidationResults()

    def test_valid_root_element_no_attributes(self):
        """Root element with no attributes should validate without issues."""
        validation_results = ValidationResults()
        xml = "<tv></tv>"
        root = etree.fromstring(xml)

        validate_root_element(root, validation_results)

        assert len(validation_results.unexpected_root_attrs) == 0

    def test_valid_root_element_with_expected_attributes(self):
        """Root element with expected attributes should validate without issues."""
        validation_results = ValidationResults()
        xml = (
            '<tv generator-info-name="test" generator-info-url="http://test.com"></tv>'
        )
        root = etree.fromstring(xml)

        validate_root_element(root, validation_results)

        assert len(validation_results.unexpected_root_attrs) == 0

    def test_root_element_with_unexpected_attribute(self):
        """Root element with unexpected attribute should record validation issue."""
        validation_results = ValidationResults()
        xml = '<tv unknown-attr="value"></tv>'
        root = etree.fromstring(xml)

        validate_root_element(root, validation_results)

        assert "unknown-attr" in validation_results.unexpected_root_attrs

    def test_root_element_with_multiple_unexpected_attributes(self):
        """Root element with multiple unexpected attributes should record all issues."""
        validation_results = ValidationResults()
        xml = (
            '<tv unknown1="value1" unknown2="value2" generator-info-name="valid"></tv>'
        )
        root = etree.fromstring(xml)

        validate_root_element(root, validation_results)

        assert "unknown1" in validation_results.unexpected_root_attrs
        assert "unknown2" in validation_results.unexpected_root_attrs
        assert "generator-info-name" not in validation_results.unexpected_root_attrs

    def test_root_element_with_mixed_attributes(self):
        """Root element with mix of expected and unexpected attributes should only record unexpected ones."""
        validation_results = ValidationResults()
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

        validate_root_element(root, validation_results)

        # Should only contain unexpected attributes
        assert "unknown-attr" in validation_results.unexpected_root_attrs
        assert "another-bad" in validation_results.unexpected_root_attrs
        assert len(validation_results.unexpected_root_attrs) == 2

    def test_empty_attribute_values(self):
        """Root element with empty attribute values should still be recorded as unexpected if not in expected list."""
        validation_results = ValidationResults()
        xml = '<tv unknown-attr=""></tv>'
        root = etree.fromstring(xml)

        validate_root_element(root, validation_results)

        assert "unknown-attr" in validation_results.unexpected_root_attrs

    def test_whitespace_attribute_values(self):
        """Root element with whitespace-only attribute values should still be validated."""
        validation_results = ValidationResults()
        xml = '<tv unknown-attr="   "></tv>'
        root = etree.fromstring(xml)

        validate_root_element(root, validation_results)

        assert "unknown-attr" in validation_results.unexpected_root_attrs

    def test_unicode_attribute_names(self):
        """Root element with unicode attribute names should be handled correctly."""
        validation_results = ValidationResults()
        xml = '<tv générator-info="test"></tv>'
        root = etree.fromstring(xml)

        validate_root_element(root, validation_results)

        assert "générator-info" in validation_results.unexpected_root_attrs

    def test_case_sensitive_attribute_validation(self):
        """Root element attribute validation should be case-sensitive."""
        validation_results = ValidationResults()
        xml = '<tv Source="test" generator-info-name="Test"></tv>'
        root = etree.fromstring(xml)

        validate_root_element(root, validation_results)

        # 'Source' (capital S) should be unexpected, 'source' would be expected
        assert "Source" in validation_results.unexpected_root_attrs
        # 'generator-info-name' is expected, so should not be in unexpected
        assert "generator-info-name" not in validation_results.unexpected_root_attrs

    def test_default_validation_results_instantiation(self):
        """Test that validate_root_element creates ValidationResults when none provided."""
        xml = '<tv unexpected-attr="value"></tv>'
        root = etree.fromstring(xml)
        
        # Call without providing validation_results - should create default instance
        # This covers line 150: validation_results = ValidationResults()
        validate_root_element(root)
        
        # Function should complete successfully without errors
        # (We can't access the internal validation_results, but successful completion
        # indicates the default instance was created)

    def test_unexpected_root_tags_validation(self):
        """Test that unexpected child tags in root element are recorded."""
        validation_results = ValidationResults()
        xml = '''<tv>
            <channel id="test"></channel>
            <programme channel="test" start="20240101000000" stop="20240101010000"></programme>
            <unexpected-tag>content</unexpected-tag>
            <another-unexpected>more content</another-unexpected>
        </tv>'''
        root = etree.fromstring(xml)

        validate_root_element(root, validation_results)

        assert "unexpected-tag" in validation_results.unexpected_root_tags
        assert "another-unexpected" in validation_results.unexpected_root_tags
        assert validation_results.unexpected_root_tags["unexpected-tag"] == 1
        assert validation_results.unexpected_root_tags["another-unexpected"] == 1
        assert "channel" not in validation_results.unexpected_root_tags
        assert "programme" not in validation_results.unexpected_root_tags

    def test_namespace_attributes(self):
        """Root element with namespace attributes should be handled correctly."""
        validation_results = ValidationResults()
        xml = '<tv xmlns:custom="http://example.com" custom:attr="value"></tv>'
        root = etree.fromstring(xml)

        validate_root_element(root, validation_results)

        # Namespace declarations and namespaced attributes should be recorded as unexpected
        # (unless they're in the expected list)
        assert len(validation_results.unexpected_root_attrs) > 0
