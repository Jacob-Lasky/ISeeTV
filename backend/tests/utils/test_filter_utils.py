"""Comprehensive tests for filter_utils.py following atomic design principles."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import text

from common.filter_utils import (
    FILTERABLE_COLUMNS_CONFIG,
    SPECIAL_FILTER_QUERIES,
    _get_filter_query,
    _precompute_column_values,
    precompute_filter_values,
    precompute_all_filter_values,
    get_filter_values,
    get_all_filter_values,
    get_table_filter_statistics,
    get_table_filter_statistics_by_source,
)
from models.db_models import FilterValueTable


class TestFilterableColumnsConfig:
    """Test the FILTERABLE_COLUMNS_CONFIG constant."""

    def test_config_structure(self):
        """Test that config has expected structure and values."""
        assert isinstance(FILTERABLE_COLUMNS_CONFIG, dict)
        assert "epg_channels" in FILTERABLE_COLUMNS_CONFIG
        assert "m3u_channels" in FILTERABLE_COLUMNS_CONFIG
        assert "programs" in FILTERABLE_COLUMNS_CONFIG
        assert "streams" in FILTERABLE_COLUMNS_CONFIG

    def test_config_values(self):
        """Test that config contains expected column lists."""
        assert FILTERABLE_COLUMNS_CONFIG["epg_channels"] == ["source", "filter_reasons"]
        assert FILTERABLE_COLUMNS_CONFIG["m3u_channels"] == ["source", "group", "stream_mode", "filter_reasons"]
        assert FILTERABLE_COLUMNS_CONFIG["programs"] == ["source", "filter_reasons"]
        assert FILTERABLE_COLUMNS_CONFIG["streams"] == ["source", "group", "stream_mode", "filter_reasons"]


class TestSpecialFilterQueries:
    """Test the SPECIAL_FILTER_QUERIES constant."""

    def test_streams_queries_exist(self):
        """Test that streams table has special queries defined."""
        assert "streams" in SPECIAL_FILTER_QUERIES
        streams_queries = SPECIAL_FILTER_QUERIES["streams"]
        assert "source" in streams_queries
        assert "group" in streams_queries
        assert "stream_mode" in streams_queries
        assert "filter_reasons" in streams_queries

    def test_query_structure(self):
        """Test that queries are properly formatted SQL strings."""
        for table, columns in SPECIAL_FILTER_QUERIES.items():
            for column, query in columns.items():
                assert isinstance(query, str)
                assert "SELECT" in query.upper()
                assert "COUNT(*)" in query.upper()


class TestGetFilterQuery:
    """Test the _get_filter_query function."""

    @pytest.mark.parametrize("table_name,column_name", [
        ("streams", "source"),
        ("streams", "group"),
        ("streams", "stream_mode"),
        ("streams", "filter_reasons"),
    ])
    def test_special_queries(self, table_name, column_name):
        """Test that special queries are returned for streams table."""
        result = _get_filter_query(table_name, column_name)
        expected = SPECIAL_FILTER_QUERIES[table_name][column_name]
        assert result == expected

    @pytest.mark.parametrize("table_name", [
        "epg_channels",
        "m3u_channels", 
        "programs",
    ])
    def test_filter_reasons_query(self, table_name):
        """Test filter_reasons query generation for regular tables."""
        result = _get_filter_query(table_name, "filter_reasons")
        assert "WITH filter_values AS" in result
        assert "CASE" in result
        assert "WHEN filter_reasons IS NULL" in result
        assert "THEN 'Passed'" in result
        assert f"FROM {table_name}" in result

    @pytest.mark.parametrize("table_name,column_name", [
        ("epg_channels", "source"),
        ("m3u_channels", "group"),
        ("programs", "source"),
    ])
    def test_standard_column_query(self, table_name, column_name):
        """Test standard column query generation."""
        result = _get_filter_query(table_name, column_name)
        assert f"SELECT `{column_name}` as value, COUNT(*) as count" in result
        assert f"FROM {table_name}" in result
        assert f"WHERE `{column_name}` IS NOT NULL" in result
        assert f"GROUP BY `{column_name}`" in result
        assert f"ORDER BY `{column_name}`" in result

    def test_column_name_escaping(self):
        """Test that column names are properly escaped with backticks."""
        result = _get_filter_query("test_table", "test_column")
        assert "`test_column`" in result

    def test_empty_strings(self):
        """Test handling of empty table and column names."""
        result = _get_filter_query("", "")
        assert "SELECT `` as value" in result
        assert "FROM " in result


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


class TestPrecomputeAllFilterValues:
    """Test the precompute_all_filter_values function."""

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
        
        assert result == {}

    def test_query_parameters(self, mock_session):
        """Test that query is called with correct parameters."""
        mock_session.execute.return_value = []
        
        get_table_filter_statistics_by_source(mock_session, "test_table", "test_source")
        
        # Verify execute was called with query and parameters
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        # SQLAlchemy text() function passes both query and parameters as positional args
        assert len(call_args[0]) == 2  # Query and parameters
        assert call_args[0][1] == {"source": "test_source"}  # Parameters

    @pytest.mark.parametrize("source_name", [
        "source1",
        "source_with_special_chars",
        "unicode_source_测试",
        "",
    ])
    def test_different_source_names(self, mock_session, source_name):
        """Test handling of different source name formats."""
        mock_session.execute.return_value = []
        
        result = get_table_filter_statistics_by_source(mock_session, "test_table", source_name)
        
        # Should handle all source names without error
        expected = {
            "filter_stats": {},
            "passed": 0,
            "all_not_passed": 0,
            "total": 0,
        }
        assert result == expected


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
            FilterValueTable(table_name="test_table", column_name="source", value="source1", count=10),
        ]
        
        with patch('common.filter_utils._precompute_column_values') as mock_precompute:
            mock_precompute.return_value = mock_filter_values
            
            # Precompute values
            precompute_filter_values(mock_session, "epg_channels")
            
            # Verify precomputation was called for each column
            expected_columns = FILTERABLE_COLUMNS_CONFIG["epg_channels"]
            assert mock_precompute.call_count == len(expected_columns)

    def test_error_resilience(self, mock_session):
        """Test that functions handle errors gracefully without crashing."""
        # All functions should handle database errors gracefully
        mock_session.execute.side_effect = Exception("Database connection lost")
        mock_session.query.side_effect = Exception("Database connection lost")
        
        # These should not raise exceptions
        assert get_filter_values(mock_session, "test_table", "source") == []
        assert get_all_filter_values(mock_session, "test_table") == {}
        assert get_table_filter_statistics(mock_session, "test_table") == {}
        assert get_table_filter_statistics_by_source(mock_session, "test_table", "source") == {}

    @pytest.mark.parametrize("table_name", list(FILTERABLE_COLUMNS_CONFIG.keys()))
    def test_all_configured_tables_supported(self, mock_session, table_name):
        """Test that all configured tables are properly supported."""
        # Should not raise exceptions for any configured table
        with patch('common.filter_utils._precompute_column_values') as mock_precompute:
            mock_precompute.return_value = []
            precompute_filter_values(mock_session, table_name)
            
        # Should handle retrieval for all tables
        assert get_filter_values(mock_session, table_name, "source") == []
        assert get_all_filter_values(mock_session, table_name) == {}
