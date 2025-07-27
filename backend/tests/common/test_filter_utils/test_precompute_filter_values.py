"""Tests for precompute_filter_values function following atomic design principles."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from common.filter_utils import (
    FILTERABLE_COLUMNS_CONFIG,
    precompute_filter_values,
)
from models.db_models import FilterValueTable


class TestPrecomputeFilterValues:
    """Test the precompute_filter_values function."""

    @pytest.fixture
    def mock_session(self):
        """Mock SQLAlchemy session with query method."""
        session = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.delete.return_value = None
        mock_query.filter.return_value = mock_filter
        session.query.return_value = mock_query
        return session

    @pytest.fixture
    def mock_filter_values(self):
        """Mock filter values for testing."""
        return [
            FilterValueTable(table_name="test_table", column_name="source", value="source1", count=10),
            FilterValueTable(table_name="test_table", column_name="group", value="group1", count=5),
        ]

    def test_successful_precompute(self, mock_session, mock_filter_values):
        """Test successful precomputation of filter values."""
        with patch('common.filter_utils._precompute_column_values') as mock_precompute:
            # m3u_channels has 4 filterable columns: source, group, stream_mode, filter_reasons
            mock_precompute.side_effect = [
                [mock_filter_values[0]],  # source column
                [mock_filter_values[1]],  # group column
                [mock_filter_values[0]],  # stream_mode column
                [mock_filter_values[1]],  # filter_reasons column
            ]
            
            precompute_filter_values(mock_session, "m3u_channels")
            
            # Verify deletion of existing values
            mock_session.query.assert_called_with(FilterValueTable)
            
            # Verify add_all and commit were called
            mock_session.add_all.assert_called_once()
            mock_session.commit.assert_called_once()

    def test_unknown_table(self, mock_session):
        """Test handling of unknown table names."""
        precompute_filter_values(mock_session, "unknown_table")
        
        # Should return early without processing
        mock_session.query.assert_not_called()
        mock_session.add_all.assert_not_called()
        mock_session.commit.assert_not_called()

    def test_no_filter_values_found(self, mock_session):
        """Test handling when no filter values are found."""
        with patch('common.filter_utils._precompute_column_values') as mock_precompute:
            mock_precompute.return_value = []
            
            precompute_filter_values(mock_session, "epg_channels")
            
            # Should clear existing but not add new values
            mock_session.query.assert_called_with(FilterValueTable)
            mock_session.add_all.assert_not_called()
            mock_session.commit.assert_not_called()

    def test_exception_handling_with_rollback(self, mock_session):
        """Test exception handling triggers rollback."""
        mock_session.query.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            precompute_filter_values(mock_session, "epg_channels")
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.parametrize("table_name", [
        "epg_channels",
        "m3u_channels",
        "programs",
        "streams",
    ])
    def test_all_configured_tables(self, mock_session, table_name):
        """Test precomputation works for all configured tables."""
        with patch('common.filter_utils._precompute_column_values') as mock_precompute:
            mock_precompute.return_value = []
            
            precompute_filter_values(mock_session, table_name)
            
            # Should process without error
            expected_columns = FILTERABLE_COLUMNS_CONFIG[table_name]
            assert mock_precompute.call_count == len(expected_columns)
