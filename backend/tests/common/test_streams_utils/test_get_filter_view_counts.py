"""Tests for get_filter_view_counts function following atomic design principles."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy import text

from common.streams_utils import get_filter_view_counts


class TestGetFilterViewCounts:
    """Atomic tests for get_filter_view_counts function."""

    def test_basic_filter_view_counts_no_filters(self, mock_session):
        """Test basic filter view counts with no filters applied."""
        # Mock the database result
        mock_row = Mock()
        mock_row.normal_count = 100
        mock_row.inverse_count = 50
        mock_row.all_count = 150
        
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = get_filter_view_counts(mock_session)

        expected_counts = {
            "normal": 100,
            "inverse": 50,
            "all": 150
        }
        assert result == expected_counts
        mock_session.execute.assert_called_once()

    def test_filter_view_counts_with_source_filter(self, mock_session):
        """Test filter view counts with source filter applied."""
        mock_row = Mock()
        mock_row.normal_count = 75
        mock_row.inverse_count = 25
        mock_row.all_count = 100
        
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = get_filter_view_counts(mock_session, source="test_source")

        assert result == {"normal": 75, "inverse": 25, "all": 100}
        
        # Verify the SQL query includes source filter
        call_args = mock_session.execute.call_args
        query_text = call_args[0][0].text
        params = call_args[0][1]
        
        assert "m.source = :source" in query_text
        assert params["source"] == "test_source"

    def test_filter_view_counts_with_group_filter(self, mock_session):
        """Test filter view counts with group filter applied."""
        mock_row = Mock()
        mock_row.normal_count = 60
        mock_row.inverse_count = 40
        mock_row.all_count = 100
        
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = get_filter_view_counts(mock_session, group="Entertainment")

        assert result == {"normal": 60, "inverse": 40, "all": 100}
        
        # Verify the SQL query includes group filter
        call_args = mock_session.execute.call_args
        query_text = call_args[0][0].text
        params = call_args[0][1]
        
        assert "m.`group` = :group" in query_text
        assert params["group"] == "Entertainment"

    def test_filter_view_counts_with_global_filter(self, mock_session):
        """Test filter view counts with global search filter applied."""
        mock_row = Mock()
        mock_row.normal_count = 30
        mock_row.inverse_count = 20
        mock_row.all_count = 50
        
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = get_filter_view_counts(mock_session, global_filter="news")

        assert result == {"normal": 30, "inverse": 20, "all": 50}
        
        # Verify the SQL query includes global filter
        call_args = mock_session.execute.call_args
        query_text = call_args[0][0].text
        params = call_args[0][1]
        
        assert "m.name LIKE :global_filter" in query_text
        assert "m.tvg_id LIKE :global_filter" in query_text
        assert "COALESCE(e.display_name, '') LIKE :global_filter" in query_text
        assert "COALESCE(m.`group`, '') LIKE :global_filter" in query_text
        assert params["global_filter"] == "%news%"

    def test_filter_view_counts_with_column_filters(self, mock_session):
        """Test filter view counts with column-specific filters applied."""
        mock_row = Mock()
        mock_row.normal_count = 15
        mock_row.inverse_count = 10
        mock_row.all_count = 25
        
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        column_filters = {
            "name": "test_channel",
            "tvg_id": "ch001",
            "group": "Sports",
            "source": "provider1"
        }

        result = get_filter_view_counts(mock_session, column_filters=column_filters)

        assert result == {"normal": 15, "inverse": 10, "all": 25}
        
        # Verify the SQL query includes all column filters
        call_args = mock_session.execute.call_args
        query_text = call_args[0][0].text
        params = call_args[0][1]
        
        assert "m.name LIKE :name_filter" in query_text
        assert "m.tvg_id LIKE :tvg_id_filter" in query_text
        assert "m.`group` = :group_filter" in query_text
        assert "m.source = :source_filter" in query_text
        
        assert params["name_filter"] == "%test_channel%"
        assert params["tvg_id_filter"] == "%ch001%"
        assert params["group_filter"] == "Sports"
        assert params["source_filter"] == "provider1"

    def test_filter_view_counts_with_all_filters_combined(self, mock_session):
        """Test filter view counts with all filter types combined."""
        mock_row = Mock()
        mock_row.normal_count = 5
        mock_row.inverse_count = 3
        mock_row.all_count = 8
        
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        column_filters = {"name": "test", "group": "News"}

        result = get_filter_view_counts(
            mock_session,
            source="test_source",
            group="Entertainment",
            global_filter="search_term",
            column_filters=column_filters
        )

        assert result == {"normal": 5, "inverse": 3, "all": 8}

    def test_filter_view_counts_with_empty_column_filters(self, mock_session):
        """Test filter view counts with empty column filters dictionary."""
        mock_row = Mock()
        mock_row.normal_count = 100
        mock_row.inverse_count = 50
        mock_row.all_count = 150
        
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = get_filter_view_counts(mock_session, column_filters={})

        assert result == {"normal": 100, "inverse": 50, "all": 150}

    def test_filter_view_counts_ignores_invalid_column_filters(self, mock_session):
        """Test that invalid column filter keys are ignored."""
        mock_row = Mock()
        mock_row.normal_count = 80
        mock_row.inverse_count = 20
        mock_row.all_count = 100
        
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        column_filters = {
            "name": "valid",
            "invalid_column": "ignored",
            "another_invalid": "also_ignored"
        }

        result = get_filter_view_counts(mock_session, column_filters=column_filters)

        assert result == {"normal": 80, "inverse": 20, "all": 100}
        
        # Verify only valid column filter is included
        call_args = mock_session.execute.call_args
        query_text = call_args[0][0].text
        params = call_args[0][1]
        
        assert "m.name LIKE :name_filter" in query_text
        assert "invalid_column" not in query_text
        assert "another_invalid" not in query_text
        assert params["name_filter"] == "%valid%"

    def test_filter_view_counts_ignores_empty_column_filter_values(self, mock_session):
        """Test that empty column filter values are ignored."""
        mock_row = Mock()
        mock_row.normal_count = 90
        mock_row.inverse_count = 10
        mock_row.all_count = 100
        
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        column_filters = {
            "name": "valid_name",
            "tvg_id": "",  # Empty string should be ignored
            "group": None,  # None should be ignored
            "source": "valid_source"
        }

        result = get_filter_view_counts(mock_session, column_filters=column_filters)

        assert result == {"normal": 90, "inverse": 10, "all": 100}
        
        # Verify only non-empty filters are included
        call_args = mock_session.execute.call_args
        query_text = call_args[0][0].text
        params = call_args[0][1]
        
        assert "m.name LIKE :name_filter" in query_text
        assert "m.source = :source_filter" in query_text
        assert "tvg_id_filter" not in params
        assert "group_filter" not in params

    def test_filter_view_counts_handles_null_counts(self, mock_session):
        """Test that null count values are handled correctly."""
        mock_row = Mock()
        mock_row.normal_count = None
        mock_row.inverse_count = None
        mock_row.all_count = None
        
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = get_filter_view_counts(mock_session)

        assert result == {"normal": 0, "inverse": 0, "all": 0}

    def test_filter_view_counts_handles_database_exception(self, mock_session):
        """Test that database exceptions are handled gracefully."""
        mock_session.execute.side_effect = Exception("Database error")

        result = get_filter_view_counts(mock_session)

        assert result == {"normal": 0, "inverse": 0, "all": 0}

    def test_filter_view_counts_handles_no_result(self, mock_session):
        """Test that no database result is handled correctly."""
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        result = get_filter_view_counts(mock_session)

        assert result == {"normal": 0, "inverse": 0, "all": 0}

    @pytest.mark.parametrize("source,group,global_filter", [
        ("source1", None, None),
        (None, "Sports", None),
        (None, None, "search"),
        ("source1", "Sports", "search"),
        ("", "", ""),
    ])
    def test_filter_view_counts_with_various_filter_combinations(self, mock_session, source, group, global_filter):
        """Test filter view counts with various filter parameter combinations."""
        mock_row = Mock()
        mock_row.normal_count = 42
        mock_row.inverse_count = 8
        mock_row.all_count = 50
        
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = get_filter_view_counts(
            mock_session,
            source=source,
            group=group,
            global_filter=global_filter
        )

        assert result == {"normal": 42, "inverse": 8, "all": 50}

    def test_sql_query_structure(self, mock_session):
        """Test that the generated SQL query has the expected structure."""
        mock_row = Mock()
        mock_row.normal_count = 10
        mock_row.inverse_count = 5
        mock_row.all_count = 15
        
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        get_filter_view_counts(mock_session)

        call_args = mock_session.execute.call_args
        query_text = call_args[0][0].text
        
        # Verify the query structure contains expected elements
        assert "SELECT" in query_text
        assert "COUNT(CASE WHEN m.filter_reasons = '[]' THEN 1 END) as normal_count" in query_text
        assert "COUNT(CASE WHEN m.filter_reasons != '[]' THEN 1 END) as inverse_count" in query_text
        assert "COUNT(*) as all_count" in query_text
        assert "FROM m3u_channels m" in query_text
        assert "LEFT JOIN epg_channels e" in query_text
        assert "LEFT JOIN (" in query_text  # Programs subquery
        assert "GROUP BY source, channel_id" in query_text
