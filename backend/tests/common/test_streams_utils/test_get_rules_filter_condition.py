"""Tests for _get_rules_filter_condition function following atomic design principles."""

import pytest
from unittest.mock import patch

from common.streams_utils import _get_rules_filter_condition


class TestGetRulesFilterCondition:
    """Atomic tests for _get_rules_filter_condition function."""

    def test_filter_view_all_returns_none(self):
        """Test that filter_view='all' returns None (no filtering)."""
        result = _get_rules_filter_condition(source="test_source", filter_view="all")
        assert result is None

    def test_filter_view_all_with_none_source_returns_none(self):
        """Test that filter_view='all' returns None regardless of source."""
        result = _get_rules_filter_condition(source=None, filter_view="all")
        assert result is None

    def test_filter_view_normal_returns_correct_condition(self):
        """Test that filter_view='normal' returns correct SQL condition."""
        result = _get_rules_filter_condition(source="test_source", filter_view="normal")
        assert result == "(m.filter_reasons = '[]')"

    def test_filter_view_normal_with_none_source_returns_correct_condition(self):
        """Test that filter_view='normal' works with None source."""
        result = _get_rules_filter_condition(source=None, filter_view="normal")
        assert result == "(m.filter_reasons = '[]')"

    def test_filter_view_inverse_returns_correct_condition(self):
        """Test that filter_view='inverse' returns correct SQL condition."""
        result = _get_rules_filter_condition(source="test_source", filter_view="inverse")
        assert result == "(m.filter_reasons != '[]')"

    def test_filter_view_inverse_with_none_source_returns_correct_condition(self):
        """Test that filter_view='inverse' works with None source."""
        result = _get_rules_filter_condition(source=None, filter_view="inverse")
        assert result == "(m.filter_reasons != '[]')"

    def test_unknown_filter_view_returns_none(self):
        """Test that unknown filter_view returns None (shows all records)."""
        result = _get_rules_filter_condition(source="test_source", filter_view="unknown")
        assert result is None

    def test_empty_filter_view_returns_none(self):
        """Test that empty filter_view returns None."""
        result = _get_rules_filter_condition(source="test_source", filter_view="")
        assert result is None

    @pytest.mark.parametrize("filter_view", ["normal", "inverse"])
    def test_debug_logging_called_for_normal_and_inverse(self, filter_view):
        """Test that debug logging is called for normal and inverse filter views."""
        with patch('common.streams_utils.logger.debug') as mock_debug:
            _get_rules_filter_condition(source="test_source", filter_view=filter_view)
            mock_debug.assert_called_once_with(
                "Applying rules filtering for filter_view: %s", filter_view
            )

    def test_info_logging_called_for_unknown_filter_view(self):
        """Test that info logging is called for unknown filter_view."""
        with patch('common.streams_utils.logger.info') as mock_info:
            _get_rules_filter_condition(source="test_source", filter_view="unknown")
            mock_info.assert_called_once_with(
                "Unknown filter_view: %s, showing all records", "unknown"
            )

    def test_no_logging_for_all_filter_view(self):
        """Test that no logging occurs for filter_view='all'."""
        with patch('common.streams_utils.logger.debug') as mock_debug, \
             patch('common.streams_utils.logger.info') as mock_info:
            _get_rules_filter_condition(source="test_source", filter_view="all")
            mock_debug.assert_not_called()
            mock_info.assert_not_called()

    @pytest.mark.parametrize("source", ["test_source", "another_source", None])
    @pytest.mark.parametrize("filter_view", ["normal", "inverse", "all", "unknown"])
    def test_function_with_various_source_and_filter_combinations(self, source, filter_view):
        """Test function with various combinations of source and filter_view parameters."""
        result = _get_rules_filter_condition(source=source, filter_view=filter_view)
        
        if filter_view == "normal":
            assert result == "(m.filter_reasons = '[]')"
        elif filter_view == "inverse":
            assert result == "(m.filter_reasons != '[]')"
        else:  # "all" or unknown
            assert result is None

    def test_default_filter_view_parameter(self):
        """Test that default filter_view parameter is 'normal'."""
        result = _get_rules_filter_condition(source="test_source")
        assert result == "(m.filter_reasons = '[]')"

    def test_case_sensitivity_of_filter_view(self):
        """Test that filter_view is case-sensitive."""
        # These should be treated as unknown and return None
        assert _get_rules_filter_condition(source="test", filter_view="NORMAL") is None
        assert _get_rules_filter_condition(source="test", filter_view="Normal") is None
        assert _get_rules_filter_condition(source="test", filter_view="ALL") is None
        assert _get_rules_filter_condition(source="test", filter_view="INVERSE") is None

    def test_whitespace_in_filter_view(self):
        """Test that whitespace in filter_view is treated as unknown."""
        assert _get_rules_filter_condition(source="test", filter_view=" normal ") is None
        assert _get_rules_filter_condition(source="test", filter_view="normal ") is None
        assert _get_rules_filter_condition(source="test", filter_view=" normal") is None
