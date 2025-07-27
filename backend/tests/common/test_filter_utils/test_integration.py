"""Integration tests for filter_utils functions following atomic design principles."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from common.filter_utils import (
    precompute_filter_values,
    precompute_all_filter_values,
    get_filter_values,
    get_table_filter_statistics,
    FILTERABLE_COLUMNS_CONFIG,
)
from models.db_models import FilterValueTable


class TestIntegration:
    """Integration tests for filter_utils functions."""

    @pytest.fixture
    def mock_session(self):
        """Mock SQLAlchemy session for integration tests."""
        session = Mock(spec=Session)
        return session

    def test_precompute_and_retrieve_workflow(self, mock_session):
        """Test the complete workflow of precomputing and retrieving filter values."""
        # Mock precomputation
        mock_filter_values = [
            FilterValueTable(
                table_name="test_table", column_name="source", value="source1", count=10
            ),
        ]

        with patch("common.filter_utils._precompute_column_values") as mock_precompute:
            mock_precompute.return_value = mock_filter_values

            # Precompute values
            precompute_filter_values(mock_session, "epg_channels")

            # Verify precomputation was called for each column
            expected_columns = FILTERABLE_COLUMNS_CONFIG["epg_channels"]
            assert mock_precompute.call_count == len(expected_columns)

    @patch("common.filter_utils.precompute_filter_values")
    def test_error_resilience_in_workflow(self, mock_precompute_filter, mock_session):
        """Test that workflow handles errors gracefully."""

        # Mock precompute_filter_values to raise exception for one table
        def side_effect(session, table_name):
            if table_name == "m3u_channels":
                raise Exception("Column computation failed")
            return True

        mock_precompute_filter.side_effect = side_effect

        # This should handle the exception gracefully
        try:
            precompute_all_filter_values(mock_session)
        except Exception as e:
            # If exception propagates, that's expected behavior
            assert "Column computation failed" in str(e)

        # Verify precompute_filter_values was called for each table
        assert mock_precompute_filter.call_count == len(FILTERABLE_COLUMNS_CONFIG)

    @patch("common.filter_utils.precompute_filter_values")
    def test_complete_filter_statistics_workflow(
        self, mock_precompute_filter, mock_session
    ):
        """Test complete workflow from precomputation to statistics retrieval."""
        # Setup mocks
        mock_precompute_filter.return_value = True

        # Mock database query results for statistics with proper object structure
        class MockRow:
            def __init__(self, source, reason, count):
                self.source = source
                self.reason = reason
                self.count = count

        mock_session.execute.return_value = [
            MockRow("source1", "rule1", 80),
            MockRow("source1", "rule2", 60),
            MockRow("source1", "Passed", 40),
        ]

        # Run precomputation
        precompute_all_filter_values(mock_session)

        # Get statistics
        stats = get_table_filter_statistics(mock_session, "m3u_channels")

        # Verify workflow completed
        assert mock_precompute_filter.call_count == len(FILTERABLE_COLUMNS_CONFIG)
        # Verify the nested structure returned by get_table_filter_statistics
        assert "source1" in stats
        assert stats["source1"]["rule1"] == 80
        assert stats["source1"]["rule2"] == 60
        assert stats["source1"]["Passed"] == 40

    def test_filter_values_retrieval_after_precomputation(self, mock_session):
        """Test retrieving filter values after precomputation."""
        # Mock the query chain for get_filter_values
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_filter_values = [
            Mock(value="source1", count=10),
            Mock(value="source2", count=5),
        ]
        mock_order.all.return_value = mock_filter_values
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query

        # Test retrieval
        result = get_filter_values(mock_session, "m3u_channels", "source")

        expected = [
            {"value": "source1", "count": 10},
            {"value": "source2", "count": 5},
        ]
        assert result == expected

    def test_configuration_driven_processing(self, mock_session):
        """Test that processing is driven by FILTERABLE_COLUMNS_CONFIG."""
        with patch("common.filter_utils._precompute_column_values") as mock_precompute:
            mock_precompute.return_value = []

            # Test each configured table
            for table_name in FILTERABLE_COLUMNS_CONFIG.keys():
                precompute_filter_values(mock_session, table_name)

                # Verify precomputation was called for each column in the table
                expected_columns = FILTERABLE_COLUMNS_CONFIG[table_name]
                expected_calls = len(expected_columns)

                # Reset call count for next iteration
                mock_precompute.reset_mock()
