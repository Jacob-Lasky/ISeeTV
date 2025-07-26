"""Tests for _precompute_column_values function following atomic design principles."""

import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session

from common.filter_utils import _precompute_column_values
from models.db_models import FilterValueTable


class TestPrecomputeColumnValues:
    """Test the _precompute_column_values function."""

    @pytest.fixture
    def mock_session(self):
        """Mock SQLAlchemy session with execute method."""
        session = Mock(spec=Session)
        return session

    @pytest.fixture
    def mock_query_result(self):
        """Mock query result with sample data."""
        mock_rows = [
            Mock(value="source1", count=10),
            Mock(value="source2", count=5),
            Mock(value="", count=3),  # Empty value should be filtered
        ]
        return mock_rows

    def test_successful_precompute(self, mock_session, mock_query_result):
        """Test successful precomputation of column values."""
        mock_session.execute.return_value = mock_query_result
        
        result = _precompute_column_values(mock_session, "test_table", "source")
        
        # Should return 2 FilterValueTable objects (empty value filtered out)
        assert len(result) == 2
        assert all(isinstance(fv, FilterValueTable) for fv in result)
        
        # Check first result
        assert result[0].table_name == "test_table"
        assert result[0].column_name == "source"
        assert result[0].value == "source1"
        assert result[0].count == 10
        
        # Check second result
        assert result[1].table_name == "test_table"
        assert result[1].column_name == "source"
        assert result[1].value == "source2"
        assert result[1].count == 5

    def test_query_execution(self, mock_session, mock_query_result):
        """Test that correct query is executed."""
        mock_session.execute.return_value = mock_query_result
        
        _precompute_column_values(mock_session, "test_table", "source")
        
        # Verify execute was called with text() wrapped query
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args[0]
        assert len(call_args) == 1
        # The query should be wrapped in text()

    def test_empty_result(self, mock_session):
        """Test handling of empty query results."""
        mock_session.execute.return_value = []
        
        result = _precompute_column_values(mock_session, "test_table", "source")
        
        assert result == []

    def test_exception_handling(self, mock_session):
        """Test exception handling and re-raising."""
        mock_session.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            _precompute_column_values(mock_session, "test_table", "source")

    @pytest.mark.parametrize("table_name,column_name", [
        ("epg_channels", "source"),
        ("m3u_channels", "group"),
        ("streams", "filter_reasons"),
    ])
    def test_different_table_column_combinations(self, mock_session, mock_query_result, table_name, column_name):
        """Test precomputation works for different table/column combinations."""
        mock_session.execute.return_value = mock_query_result
        
        result = _precompute_column_values(mock_session, table_name, column_name)
        
        assert len(result) == 2
        assert all(fv.table_name == table_name for fv in result)
        assert all(fv.column_name == column_name for fv in result)
