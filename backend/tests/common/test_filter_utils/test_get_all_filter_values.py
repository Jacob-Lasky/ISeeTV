"""Tests for get_all_filter_values function following atomic design principles."""

import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session

from common.filter_utils import get_all_filter_values
from models.db_models import FilterValueTable


class TestGetAllFilterValues:
    """Test the get_all_filter_values function."""

    @pytest.fixture
    def mock_session(self):
        """Mock SQLAlchemy session with query method."""
        session = Mock(spec=Session)
        return session

    @pytest.fixture
    def mock_filter_values(self):
        """Mock FilterValueTable objects with multiple columns."""
        return [
            Mock(column_name="source", value="source1", count=10),
            Mock(column_name="source", value="source2", count=5),
            Mock(column_name="group", value="group1", count=8),
            Mock(column_name="group", value="group2", count=3),
        ]

    def test_successful_retrieval(self, mock_session, mock_filter_values):
        """Test successful retrieval of all filter values."""
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_order.all.return_value = mock_filter_values
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        result = get_all_filter_values(mock_session, "test_table")
        
        expected = {
            "source": [
                {"value": "source1", "count": 10},
                {"value": "source2", "count": 5},
            ],
            "group": [
                {"value": "group1", "count": 8},
                {"value": "group2", "count": 3},
            ],
        }
        assert result == expected

    def test_empty_result(self, mock_session):
        """Test handling of empty results."""
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_order.all.return_value = []
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        result = get_all_filter_values(mock_session, "test_table")
        
        assert result == {}

    def test_exception_handling(self, mock_session):
        """Test exception handling returns empty dict."""
        mock_session.query.side_effect = Exception("Database error")
        
        result = get_all_filter_values(mock_session, "test_table")
        
        assert result == {}

    def test_single_column_result(self, mock_session):
        """Test handling of single column results."""
        mock_filter_values = [
            Mock(column_name="source", value="source1", count=10),
        ]
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_order.all.return_value = mock_filter_values
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        result = get_all_filter_values(mock_session, "test_table")
        
        expected = {
            "source": [{"value": "source1", "count": 10}],
        }
        assert result == expected
