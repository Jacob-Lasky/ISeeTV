"""Tests for precompute_all_filter_values function following atomic design principles."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from common.filter_utils import (
    FILTERABLE_COLUMNS_CONFIG,
    precompute_all_filter_values,
)


class TestPrecomputeAllFilterValues:
    """Test the precompute_all_filter_values function."""

    @pytest.fixture
    def mock_session(self):
        """Mock SQLAlchemy session."""
        return Mock(spec=Session)

    def test_processes_all_tables(self, mock_session):
        """Test that all configured tables are processed."""
        with patch('common.filter_utils.precompute_filter_values') as mock_precompute:
            precompute_all_filter_values(mock_session)
            
            # Should call precompute_filter_values for each table
            expected_calls = len(FILTERABLE_COLUMNS_CONFIG)
            assert mock_precompute.call_count == expected_calls
            
            # Verify all table names were processed
            called_tables = {call[0][1] for call in mock_precompute.call_args_list}
            expected_tables = set(FILTERABLE_COLUMNS_CONFIG.keys())
            assert called_tables == expected_tables

    def test_continues_on_individual_failures(self, mock_session):
        """Test that processing continues even if individual tables fail."""
        with patch('common.filter_utils.precompute_filter_values') as mock_precompute:
            # Make first table fail, others succeed
            mock_precompute.side_effect = [
                Exception("First table error"),
                None,  # Second table succeeds
                None,  # Third table succeeds
                None,  # Fourth table succeeds
            ]
            
            # Should not raise exception
            precompute_all_filter_values(mock_session)
            
            # Should still process all tables
            assert mock_precompute.call_count == len(FILTERABLE_COLUMNS_CONFIG)
