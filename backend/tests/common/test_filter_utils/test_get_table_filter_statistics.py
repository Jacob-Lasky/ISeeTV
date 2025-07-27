"""Tests for get_table_filter_statistics function following atomic design principles."""

import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session

from common.filter_utils import get_table_filter_statistics


class TestGetTableFilterStatistics:
    """Test the get_table_filter_statistics function."""

    @pytest.fixture
    def mock_session(self):
        """Mock SQLAlchemy session with execute method."""
        session = Mock(spec=Session)
        return session

    @pytest.fixture
    def mock_query_result(self):
        """Mock query result with filter statistics."""
        return [
            Mock(source="source1", reason="Passed", count=100),
            Mock(source="source1", reason="Blacklisted by rule", count=50),
            Mock(source="source2", reason="Passed", count=75),
            Mock(source="source2", reason="Whitelisted by rule", count=25),
        ]

    def test_successful_statistics_retrieval(self, mock_session, mock_query_result):
        """Test successful retrieval of filter statistics."""
        mock_session.execute.return_value = mock_query_result
        
        result = get_table_filter_statistics(mock_session, "test_table")
        
        expected = {
            "source1": {
                "Passed": 100,
                "Blacklisted by rule": 50,
            },
            "source2": {
                "Passed": 75,
                "Whitelisted by rule": 25,
            },
        }
        assert result == expected

    def test_empty_result(self, mock_session):
        """Test handling of empty query results."""
        mock_session.execute.return_value = []
        
        result = get_table_filter_statistics(mock_session, "test_table")
        
        assert result == {}

    def test_exception_handling(self, mock_session):
        """Test exception handling returns empty dict."""
        mock_session.execute.side_effect = Exception("Database error")
        
        result = get_table_filter_statistics(mock_session, "test_table")
        
        assert result == {}

    def test_query_structure(self, mock_session):
        """Test that query is properly structured."""
        mock_session.execute.return_value = []
        
        get_table_filter_statistics(mock_session, "test_table")
        
        # Verify execute was called with text() wrapped query
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args[0]
        assert len(call_args) == 1

    def test_single_source_result(self, mock_session):
        """Test handling of single source results."""
        mock_result = [
            Mock(source="source1", reason="Passed", count=100),
        ]
        mock_session.execute.return_value = mock_result
        
        result = get_table_filter_statistics(mock_session, "test_table")
        
        expected = {
            "source1": {"Passed": 100},
        }
        assert result == expected
