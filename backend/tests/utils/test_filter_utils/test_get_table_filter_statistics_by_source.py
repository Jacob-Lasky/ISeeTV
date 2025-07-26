"""Tests for get_table_filter_statistics_by_source function following atomic design principles."""

import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session

from common.filter_utils import get_table_filter_statistics_by_source


class TestGetTableFilterStatisticsBySource:
    """Test the get_table_filter_statistics_by_source function."""

    @pytest.fixture
    def mock_session(self):
        """Mock SQLAlchemy session with execute method."""
        session = Mock(spec=Session)
        return session

    @pytest.fixture
    def mock_query_result(self):
        """Mock query result with source-specific filter statistics."""
        return [
            Mock(reason="Passed", count=100),
            Mock(reason="assignment1", count=25),
            Mock(reason="assignment2", count=15),
        ]

    def test_successful_statistics_retrieval(self, mock_session, mock_query_result):
        """Test successful retrieval of source-specific filter statistics."""
        mock_session.execute.return_value = mock_query_result
        
        result = get_table_filter_statistics_by_source(mock_session, "test_table", "test_source")
        
        expected = {
            "filter_stats": {
                "Passed": 100,
                "assignment1": 25,
                "assignment2": 15,
            },
            "passed": 100,
            "all_not_passed": 40,  # 25 + 15
            "total": 140,  # 100 + 25 + 15
        }
        assert result == expected

    def test_only_passed_records(self, mock_session):
        """Test handling when only passed records exist."""
        mock_result = [Mock(reason="Passed", count=100)]
        mock_session.execute.return_value = mock_result
        
        result = get_table_filter_statistics_by_source(mock_session, "test_table", "test_source")
        
        expected = {
            "filter_stats": {"Passed": 100},
            "passed": 100,
            "all_not_passed": 0,
            "total": 100,
        }
        assert result == expected

    def test_no_passed_records(self, mock_session):
        """Test handling when no passed records exist."""
        mock_result = [
            Mock(reason="assignment1", count=25),
            Mock(reason="assignment2", count=15),
        ]
        mock_session.execute.return_value = mock_result
        
        result = get_table_filter_statistics_by_source(mock_session, "test_table", "test_source")
        
        expected = {
            "filter_stats": {
                "assignment1": 25,
                "assignment2": 15,
            },
            "passed": 0,
            "all_not_passed": 40,
            "total": 40,
        }
        assert result == expected

    def test_empty_result(self, mock_session):
        """Test handling of empty query results."""
        mock_session.execute.return_value = []
        
        result = get_table_filter_statistics_by_source(mock_session, "test_table", "test_source")
        
        expected = {
            "filter_stats": {},
            "passed": 0,
            "all_not_passed": 0,
            "total": 0,
        }
        assert result == expected

    def test_exception_handling(self, mock_session):
        """Test exception handling returns empty dict."""
        mock_session.execute.side_effect = Exception("Database error")
        
        result = get_table_filter_statistics_by_source(mock_session, "test_table", "test_source")
        
        # Function returns {} on exception, not structured dict
        assert result == {}

    def test_query_parameters(self, mock_session):
        """Test that correct query parameters are used."""
        mock_session.execute.return_value = []
        
        get_table_filter_statistics_by_source(mock_session, "test_table", "test_source")
        
        # Verify execute was called with query and parameters
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args[0]
        # SQLAlchemy text() function passes both query and parameters as positional args
        assert len(call_args) == 2  # Query and parameters
        assert call_args[1] == {"source": "test_source"}  # Parameters
