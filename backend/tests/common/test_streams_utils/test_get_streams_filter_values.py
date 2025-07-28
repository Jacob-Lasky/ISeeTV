"""Tests for get_streams_filter_values function following atomic design principles."""

import pytest
from unittest.mock import Mock, patch

from common.streams_utils import get_streams_filter_values


class TestGetStreamsFilterValues:
    """Atomic tests for get_streams_filter_values function."""

    @patch('common.streams_utils.get_all_filter_values')
    def test_basic_filter_values_success(self, mock_get_all_filter_values, mock_session):
        """Test basic filter values retrieval with successful response."""
        # Mock the response from get_all_filter_values
        mock_filter_values = {
            "source": ["source1", "source2", "source3"],
            "group": ["Entertainment", "Sports", "News"],
            "display_name": ["Channel 1", "Channel 2", "Channel 3"]
        }
        mock_get_all_filter_values.return_value = mock_filter_values

        result = get_streams_filter_values(mock_session, "test_source")

        assert result == mock_filter_values
        mock_get_all_filter_values.assert_called_once_with(mock_session, "streams")

    @patch('common.streams_utils.get_all_filter_values')
    def test_filter_values_with_empty_response(self, mock_get_all_filter_values, mock_session):
        """Test filter values retrieval with empty response."""
        mock_get_all_filter_values.return_value = {}

        result = get_streams_filter_values(mock_session, "test_source")

        assert result == {}
        mock_get_all_filter_values.assert_called_once_with(mock_session, "streams")

    @patch('common.streams_utils.get_all_filter_values')
    def test_filter_values_with_partial_data(self, mock_get_all_filter_values, mock_session):
        """Test filter values retrieval with partial data."""
        # Mock response with only some filter types
        mock_filter_values = {
            "source": ["source1", "source2"],
            "group": []  # Empty group list
        }
        mock_get_all_filter_values.return_value = mock_filter_values

        result = get_streams_filter_values(mock_session, "test_source")

        assert result == mock_filter_values
        assert result["source"] == ["source1", "source2"]
        assert result["group"] == []
        mock_get_all_filter_values.assert_called_once_with(mock_session, "streams")

    @patch('common.streams_utils.get_all_filter_values')
    def test_filter_values_with_none_response(self, mock_get_all_filter_values, mock_session):
        """Test filter values retrieval when get_all_filter_values returns None."""
        mock_get_all_filter_values.return_value = None

        result = get_streams_filter_values(mock_session, "test_source")

        assert result is None
        mock_get_all_filter_values.assert_called_once_with(mock_session, "streams")

    @patch('common.streams_utils.get_all_filter_values')
    def test_filter_values_with_unicode_data(self, mock_get_all_filter_values, mock_session):
        """Test filter values retrieval with unicode characters."""
        mock_filter_values = {
            "source": ["测试源", "مصدر الاختبار", "тестовый источник"],
            "group": ["娱乐", "رياضة", "новости"],
            "display_name": ["频道1", "قناة 2", "канал 3"]
        }
        mock_get_all_filter_values.return_value = mock_filter_values

        result = get_streams_filter_values(mock_session, "test_source")

        assert result == mock_filter_values
        assert "测试源" in result["source"]
        assert "娱乐" in result["group"]
        assert "频道1" in result["display_name"]
        mock_get_all_filter_values.assert_called_once_with(mock_session, "streams")

    @patch('common.streams_utils.get_all_filter_values')
    def test_filter_values_with_large_dataset(self, mock_get_all_filter_values, mock_session):
        """Test filter values retrieval with large dataset."""
        # Create large mock dataset
        large_sources = [f"source_{i}" for i in range(1000)]
        large_groups = [f"group_{i}" for i in range(500)]
        large_display_names = [f"channel_{i}" for i in range(2000)]
        
        mock_filter_values = {
            "source": large_sources,
            "group": large_groups,
            "display_name": large_display_names
        }
        mock_get_all_filter_values.return_value = mock_filter_values

        result = get_streams_filter_values(mock_session, "test_source")

        assert result == mock_filter_values
        assert len(result["source"]) == 1000
        assert len(result["group"]) == 500
        assert len(result["display_name"]) == 2000
        mock_get_all_filter_values.assert_called_once_with(mock_session, "streams")

    @patch('common.streams_utils.get_all_filter_values')
    def test_filter_values_with_duplicate_values(self, mock_get_all_filter_values, mock_session):
        """Test filter values retrieval with duplicate values (should be handled by get_all_filter_values)."""
        mock_filter_values = {
            "source": ["source1", "source1", "source2"],  # Duplicates
            "group": ["Sports", "Sports", "News"],  # Duplicates
            "display_name": ["Channel 1", "Channel 1", "Channel 2"]  # Duplicates
        }
        mock_get_all_filter_values.return_value = mock_filter_values

        result = get_streams_filter_values(mock_session, "test_source")

        # The function should return exactly what get_all_filter_values returns
        # Deduplication is handled by get_all_filter_values, not this function
        assert result == mock_filter_values
        mock_get_all_filter_values.assert_called_once_with(mock_session, "streams")

    @patch('common.streams_utils.get_all_filter_values')
    def test_filter_values_with_special_characters(self, mock_get_all_filter_values, mock_session):
        """Test filter values retrieval with special characters and symbols."""
        mock_filter_values = {
            "source": ["source@test.com", "source#1", "source$pecial"],
            "group": ["Group & Co", "Group/Subgroup", "Group-Name"],
            "display_name": ["Channel (HD)", "Channel [4K]", "Channel {Premium}"]
        }
        mock_get_all_filter_values.return_value = mock_filter_values

        result = get_streams_filter_values(mock_session, "test_source")

        assert result == mock_filter_values
        assert "source@test.com" in result["source"]
        assert "Group & Co" in result["group"]
        assert "Channel (HD)" in result["display_name"]
        mock_get_all_filter_values.assert_called_once_with(mock_session, "streams")

    @patch('common.streams_utils.get_all_filter_values')
    def test_filter_values_exception_handling(self, mock_get_all_filter_values, mock_session):
        """Test that exceptions are properly handled and return empty dict."""
        mock_get_all_filter_values.side_effect = Exception("Database connection error")

        result = get_streams_filter_values(mock_session, "test_source")
        
        # Function should catch exception and return empty dict
        assert result == {}
        mock_get_all_filter_values.assert_called_once_with(mock_session, "streams")

    @patch('common.streams_utils.get_all_filter_values')
    def test_filter_values_session_parameter_passed_correctly(self, mock_get_all_filter_values, mock_session):
        """Test that the session parameter is passed correctly to get_all_filter_values."""
        mock_filter_values = {"source": ["test"]}
        mock_get_all_filter_values.return_value = mock_filter_values

        # Create a specific mock session to verify it's passed through
        specific_session = Mock()
        result = get_streams_filter_values(specific_session, "test_source")

        assert result == mock_filter_values
        mock_get_all_filter_values.assert_called_once_with(specific_session, "streams")

    @patch('common.streams_utils.get_all_filter_values')
    def test_filter_values_table_name_parameter(self, mock_get_all_filter_values, mock_session):
        """Test that the correct table name is passed to get_all_filter_values."""
        mock_filter_values = {"source": ["test"]}
        mock_get_all_filter_values.return_value = mock_filter_values

        result = get_streams_filter_values(mock_session, "test_source")

        assert result == mock_filter_values
        # Verify that "m3u_channels" is passed as the table name
        mock_get_all_filter_values.assert_called_once_with(mock_session, "streams")

    @patch('common.streams_utils.get_all_filter_values')
    def test_filter_values_return_type_preservation(self, mock_get_all_filter_values, mock_session):
        """Test that the return type from get_all_filter_values is preserved."""
        # Test with different return types
        test_cases = [
            {"source": ["test"]},  # Dictionary
            {},  # Empty dictionary
            None,  # None value
        ]

        for expected_return in test_cases:
            mock_get_all_filter_values.return_value = expected_return
            result = get_streams_filter_values(mock_session, "test_source")
            assert result == expected_return
            assert type(result) == type(expected_return)

    @patch('common.streams_utils.get_all_filter_values')
    def test_filter_values_with_mixed_data_types(self, mock_get_all_filter_values, mock_session):
        """Test filter values with mixed data types in lists."""
        mock_filter_values = {
            "source": ["string_source", 123, None],  # Mixed types
            "group": ["Group1", "", "Group2"],  # Including empty string
            "display_name": ["Channel", "  ", "Another Channel"]  # Including whitespace
        }
        mock_get_all_filter_values.return_value = mock_filter_values

        result = get_streams_filter_values(mock_session, "test_source")

        # The function should pass through whatever get_all_filter_values returns
        assert result == mock_filter_values
        mock_get_all_filter_values.assert_called_once_with(mock_session, "streams")

    @patch('common.streams_utils.get_all_filter_values')
    def test_filter_values_with_unexpected_structure(self, mock_get_all_filter_values, mock_session):
        """Test filter values with unexpected data structure."""
        # Test with non-standard structure that get_all_filter_values might return
        mock_filter_values = {
            "unexpected_key": ["value1", "value2"],
            "nested": {"inner": ["nested_value"]},
            "number_key": 12345
        }
        mock_get_all_filter_values.return_value = mock_filter_values

        result = get_streams_filter_values(mock_session, "test_source")

        # Function should pass through whatever structure is returned
        assert result == mock_filter_values
        assert result["unexpected_key"] == ["value1", "value2"]
        assert result["nested"] == {"inner": ["nested_value"]}
        assert result["number_key"] == 12345
        mock_get_all_filter_values.assert_called_once_with(mock_session, "streams")
