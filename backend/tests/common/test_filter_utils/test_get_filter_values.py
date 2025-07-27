"""Tests for get_filter_values function following atomic design principles."""

import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session

from common.filter_utils import get_filter_values
from models.db_models import FilterValueTable


class TestGetFilterValues:
    """Test the get_filter_values function."""

    @pytest.fixture
    def mock_session(self):
        """Mock SQLAlchemy session with query method."""
        session = Mock(spec=Session)
        return session

    @pytest.fixture
    def mock_filter_values(self):
        """Mock FilterValueTable objects."""
        return [
            Mock(value="source1", count=10),
            Mock(value="source2", count=5),
        ]

    def test_successful_retrieval(self, mock_session, mock_filter_values):
        """Test successful retrieval of filter values."""
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_order.all.return_value = mock_filter_values
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        result = get_filter_values(mock_session, "test_table", "source")
        
        expected = [
            {"value": "source1", "count": 10},
            {"value": "source2", "count": 5},
        ]
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
        
        result = get_filter_values(mock_session, "test_table", "source")
        
        assert result == []

    def test_exception_handling(self, mock_session):
        """Test exception handling returns empty list."""
        mock_session.query.side_effect = Exception("Database error")
        
        result = get_filter_values(mock_session, "test_table", "source")
        
        assert result == []

    def test_query_parameters(self, mock_session):
        """Test that correct query parameters are used."""
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_order.all.return_value = []
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        get_filter_values(mock_session, "test_table", "test_column")
        
        # Verify query was called with FilterValueTable
        mock_session.query.assert_called_with(FilterValueTable)
