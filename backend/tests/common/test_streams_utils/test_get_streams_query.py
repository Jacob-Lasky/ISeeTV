"""Tests for get_streams_query function following atomic design principles."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from common.streams_utils import get_streams_query
from models.stream_models import StreamChannel


class TestGetStreamsQuery:
    """Atomic tests for get_streams_query function."""

    @pytest.fixture
    def mock_db_row(self):
        """Mock database row with all required fields."""
        mock_row = Mock()
        mock_row.m3u_id = 1
        mock_row.source = "test_source"
        mock_row.tvg_id = "ch001"
        mock_row.name = "Test Channel"
        mock_row.stream_url = "http://example.com/stream.m3u8"
        mock_row.logo_url = "http://example.com/logo.png"
        mock_row.group = "Entertainment"
        mock_row.stream_mode = "live"
        mock_row.epg_id = 2
        mock_row.display_name = "Test Channel Display"
        mock_row.icon_url = "http://example.com/icon.png"
        mock_row.created_at = "2024-01-01T12:00:00"
        mock_row.updated_at = "2024-01-02T12:00:00"
        mock_row.program_count = 5
        mock_row.next_program_title = "Next Program"
        mock_row.next_program_start = "2024-01-03T15:00:00"
        return mock_row

    @pytest.fixture
    def mock_count_row(self):
        """Mock count query result."""
        mock_row = Mock()
        mock_row.total = 100
        return mock_row

    def test_basic_streams_query_no_filters(self, mock_session, mock_db_row, mock_count_row):
        """Test basic streams query with no filters applied."""
        # Mock count query result
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        # Mock main query result
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_db_row]))
        
        # Configure session to return different results for count vs main query
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(mock_session)

        assert total_count == 100
        assert len(streams) == 1
        assert isinstance(streams[0], StreamChannel)
        assert streams[0].name == "Test Channel"
        assert streams[0].source == "test_source"
        assert streams[0].tvg_id == "ch001"

    def test_streams_query_with_source_filter(self, mock_session, mock_db_row, mock_count_row):
        """Test streams query with source filter applied."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_db_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(mock_session, source="test_source")

        assert total_count == 100
        assert len(streams) == 1
        
        # Verify source filter is applied in both queries
        assert mock_session.execute.call_count == 2
        for call in mock_session.execute.call_args_list:
            query_text = call[0][0].text
            params = call[0][1]
            assert "m.source = :source" in query_text
            assert params["source"] == "test_source"

    def test_streams_query_with_group_filter(self, mock_session, mock_db_row, mock_count_row):
        """Test streams query with group filter applied."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_db_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(mock_session, group="Entertainment")

        assert total_count == 100
        assert len(streams) == 1
        
        # Verify group filter is applied
        for call in mock_session.execute.call_args_list:
            query_text = call[0][0].text
            params = call[0][1]
            assert "m.`group` = :group" in query_text
            assert params["group"] == "Entertainment"

    def test_streams_query_with_global_filter(self, mock_session, mock_db_row, mock_count_row):
        """Test streams query with global search filter applied."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_db_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(mock_session, global_filter="test")

        assert total_count == 100
        assert len(streams) == 1
        
        # Verify global filter is applied
        for call in mock_session.execute.call_args_list:
            query_text = call[0][0].text
            params = call[0][1]
            assert "m.name LIKE :global_filter" in query_text
            assert "m.tvg_id LIKE :global_filter" in query_text
            assert "e.display_name LIKE :global_filter" in query_text
            assert "m.`group` LIKE :global_filter" in query_text
            assert params["global_filter"] == "%test%"

    def test_streams_query_with_column_filters(self, mock_session, mock_db_row, mock_count_row):
        """Test streams query with column-specific filters applied."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_db_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        column_filters = {
            "name": "test_channel",
            "tvg_id": "ch001",
            "display_name": "display",
            "group": "Sports",
            "source": "provider1"
        }

        streams, total_count = get_streams_query(mock_session, column_filters=column_filters)

        assert total_count == 100
        assert len(streams) == 1
        
        # Verify all column filters are applied
        for call in mock_session.execute.call_args_list:
            query_text = call[0][0].text
            params = call[0][1]
            assert "m.name LIKE :name_filter" in query_text
            assert "m.tvg_id LIKE :tvg_id_filter" in query_text
            assert "e.display_name LIKE :display_name_filter" in query_text
            assert "m.`group` = :group_filter" in query_text
            assert "m.source = :source_filter" in query_text
            
            assert params["name_filter"] == "%test_channel%"
            assert params["tvg_id_filter"] == "%ch001%"
            assert params["display_name_filter"] == "%display%"
            assert params["group_filter"] == "Sports"
            assert params["source_filter"] == "provider1"

    @patch('common.streams_utils._get_rules_filter_condition')
    def test_streams_query_with_rules_filtering_enabled(self, mock_rules_filter, mock_session, mock_db_row, mock_count_row):
        """Test streams query with rules filtering enabled."""
        mock_rules_filter.return_value = "(m.filter_reasons = '[]')"
        
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_db_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(
            mock_session, 
            source="test_source",
            apply_rules=True,
            filter_view="normal"
        )

        assert total_count == 100
        assert len(streams) == 1
        
        # Verify rules filter function was called
        mock_rules_filter.assert_called_with("test_source", "normal")
        
        # Verify rules condition is applied in query
        for call in mock_session.execute.call_args_list:
            query_text = call[0][0].text
            assert "(m.filter_reasons = '[]')" in query_text

    @patch('common.streams_utils._get_rules_filter_condition')
    def test_streams_query_with_rules_filtering_disabled(self, mock_rules_filter, mock_session, mock_db_row, mock_count_row):
        """Test streams query with rules filtering disabled."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_db_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(mock_session, apply_rules=False)

        assert total_count == 100
        assert len(streams) == 1
        
        # Verify rules filter function was not called
        mock_rules_filter.assert_not_called()

    @pytest.mark.parametrize("sort_field,sort_order,expected_field,expected_order", [
        ("name", "asc", "m.name", "ASC"),
        ("name", "desc", "m.name", "DESC"),
        ("tvg_id", "asc", "m.tvg_id", "ASC"),
        ("display_name", "desc", "e.display_name", "DESC"),
        ("group", "asc", "m.`group`", "ASC"),
        ("source", "desc", "m.source", "DESC"),
        ("program_count", "asc", "program_count", "ASC"),
        ("created_at", "desc", "m.created_at", "DESC"),
        ("updated_at", "asc", "m.updated_at", "ASC"),
    ])
    def test_streams_query_sorting(self, mock_session, mock_db_row, mock_count_row, 
                                 sort_field, sort_order, expected_field, expected_order):
        """Test streams query with various sorting options."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_db_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(
            mock_session, 
            sort_field=sort_field, 
            sort_order=sort_order
        )

        assert total_count == 100
        assert len(streams) == 1
        
        # Verify sorting is applied in main query (second call)
        main_query_call = mock_session.execute.call_args_list[1]
        query_text = main_query_call[0][0].text
        expected_order_by = f"ORDER BY {expected_field} {expected_order}"
        assert expected_order_by in query_text

    def test_streams_query_invalid_sort_field_defaults_to_name(self, mock_session, mock_db_row, mock_count_row):
        """Test that invalid sort field defaults to 'name'."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_db_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(mock_session, sort_field="invalid_field")

        assert total_count == 100
        assert len(streams) == 1
        
        # Verify default sorting is applied
        main_query_call = mock_session.execute.call_args_list[1]
        query_text = main_query_call[0][0].text
        assert "ORDER BY m.name ASC" in query_text

    def test_streams_query_invalid_sort_order_defaults_to_asc(self, mock_session, mock_db_row, mock_count_row):
        """Test that invalid sort order defaults to 'asc'."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_db_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(mock_session, sort_order="invalid_order")

        assert total_count == 100
        assert len(streams) == 1
        
        # Verify default sort order is applied
        main_query_call = mock_session.execute.call_args_list[1]
        query_text = main_query_call[0][0].text
        assert "ORDER BY m.name ASC" in query_text

    def test_streams_query_pagination(self, mock_session, mock_db_row, mock_count_row):
        """Test streams query pagination parameters."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_db_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(mock_session, page=2, page_size=50)

        assert total_count == 100
        assert len(streams) == 1
        
        # Verify pagination parameters
        main_query_call = mock_session.execute.call_args_list[1]
        query_text = main_query_call[0][0].text
        params = main_query_call[0][1]
        
        assert "LIMIT :limit OFFSET :offset" in query_text
        assert params["limit"] == 50
        assert params["offset"] == 50  # (page-1) * page_size = (2-1) * 50 = 50

    def test_streams_query_datetime_conversion_string_input(self, mock_session, mock_count_row):
        """Test datetime conversion when database returns string dates."""
        # Mock row with string datetime values
        mock_row = Mock()
        mock_row.m3u_id = 1
        mock_row.source = "test_source"
        mock_row.tvg_id = "ch001"
        mock_row.name = "Test Channel"
        mock_row.stream_url = "http://example.com/stream.m3u8"
        mock_row.logo_url = "http://example.com/logo.png"
        mock_row.group = "Entertainment"
        mock_row.stream_mode = "live"
        mock_row.epg_id = 2
        mock_row.display_name = "Test Channel Display"
        mock_row.icon_url = "http://example.com/icon.png"
        mock_row.created_at = "2024-01-01T12:00:00"
        mock_row.updated_at = "2024-01-02T12:00:00"
        mock_row.program_count = 5
        mock_row.next_program_title = "Next Program"
        mock_row.next_program_start = "2024-01-03T15:00:00"
        
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(mock_session)

        assert len(streams) == 1
        stream = streams[0]
        
        # Verify datetime conversion
        assert isinstance(stream.created_at, datetime)
        assert isinstance(stream.updated_at, datetime)
        assert isinstance(stream.next_program_start, datetime)
        assert stream.created_at.year == 2024
        assert stream.created_at.month == 1
        assert stream.created_at.day == 1

    def test_streams_query_datetime_conversion_datetime_input(self, mock_session, mock_count_row):
        """Test datetime handling when database returns datetime objects."""
        created_dt = datetime(2024, 1, 1, 12, 0, 0)
        updated_dt = datetime(2024, 1, 2, 12, 0, 0)
        next_program_dt = datetime(2024, 1, 3, 15, 0, 0)
        
        # Mock row with datetime objects
        mock_row = Mock()
        mock_row.m3u_id = 1
        mock_row.source = "test_source"
        mock_row.tvg_id = "ch001"
        mock_row.name = "Test Channel"
        mock_row.stream_url = "http://example.com/stream.m3u8"
        mock_row.logo_url = "http://example.com/logo.png"
        mock_row.group = "Entertainment"
        mock_row.stream_mode = "live"
        mock_row.epg_id = 2
        mock_row.display_name = "Test Channel Display"
        mock_row.icon_url = "http://example.com/icon.png"
        mock_row.created_at = created_dt
        mock_row.updated_at = updated_dt
        mock_row.program_count = 5
        mock_row.next_program_title = "Next Program"
        mock_row.next_program_start = next_program_dt
        
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(mock_session)

        assert len(streams) == 1
        stream = streams[0]
        
        # Verify datetime objects are preserved
        assert stream.created_at == created_dt
        assert stream.updated_at == updated_dt
        assert stream.next_program_start == next_program_dt

    def test_streams_query_handles_null_values(self, mock_session, mock_count_row):
        """Test streams query handles null/None values correctly."""
        # Mock row with null values
        mock_row = Mock()
        mock_row.m3u_id = 1
        mock_row.source = "test_source"
        mock_row.tvg_id = "ch001"
        mock_row.name = "Test Channel"
        mock_row.stream_url = "http://example.com/stream.m3u8"
        mock_row.logo_url = None
        mock_row.group = None
        mock_row.stream_mode = "live"
        mock_row.epg_id = None
        mock_row.display_name = None
        mock_row.icon_url = None
        mock_row.created_at = "2024-01-01T12:00:00"
        mock_row.updated_at = "2024-01-02T12:00:00"
        mock_row.program_count = None
        mock_row.next_program_title = None
        mock_row.next_program_start = None
        
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(mock_session)

        assert len(streams) == 1
        stream = streams[0]
        
        # Verify null values are handled correctly
        assert stream.logo_url is None
        assert stream.group is None
        assert stream.epg_id is None
        assert stream.display_name is None
        assert stream.icon_url is None
        assert stream.program_count == 0  # Should default to 0
        assert stream.next_program_title is None
        assert stream.next_program_start is None

    def test_streams_query_handles_database_exception(self, mock_session):
        """Test that database exceptions are propagated."""
        mock_session.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            get_streams_query(mock_session)

    def test_streams_query_empty_result(self, mock_session, mock_count_row):
        """Test streams query with empty result set."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        streams, total_count = get_streams_query(mock_session)

        assert total_count == 100
        assert len(streams) == 0
        assert streams == []

    def test_streams_query_ignores_empty_column_filter_values(self, mock_session, mock_db_row, mock_count_row):
        """Test that empty column filter values are ignored."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_db_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        column_filters = {
            "name": "valid_name",
            "tvg_id": "",  # Empty string should be ignored
            "group": None,  # None should be ignored
            "source": "valid_source"
        }

        streams, total_count = get_streams_query(mock_session, column_filters=column_filters)

        assert total_count == 100
        assert len(streams) == 1
        
        # Verify only non-empty filters are included
        for call in mock_session.execute.call_args_list:
            query_text = call[0][0].text
            params = call[0][1]
            
            assert "m.name LIKE :name_filter" in query_text
            assert "m.source = :source_filter" in query_text
            assert "tvg_id_filter" not in params
            assert "group_filter" not in params

    def test_sql_query_structure(self, mock_session, mock_db_row, mock_count_row):
        """Test that the generated SQL query has the expected structure."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_db_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        get_streams_query(mock_session)

        # Verify count query structure
        count_query_call = mock_session.execute.call_args_list[0]
        count_query_text = count_query_call[0][0].text
        assert "SELECT COUNT(*) as total" in count_query_text
        
        # Verify main query structure
        main_query_call = mock_session.execute.call_args_list[1]
        main_query_text = main_query_call[0][0].text
        
        # Check for expected SELECT fields
        expected_fields = [
            "m.id as m3u_id",
            "m.source",
            "m.tvg_id",
            "m.name",
            "m.stream_url",
            "m.logo_url",
            "m.`group`",
            "m.stream_mode",
            "e.id as epg_id",
            "e.display_name",
            "e.icon_url",
            "m.created_at",
            "m.updated_at",
            "m.filter_reasons",
            "COALESCE(p.program_count, 0) as program_count",
            "p.next_program_title",
            "p.next_program_start"
        ]
        
        for field in expected_fields:
            assert field in main_query_text
        
        # Check for expected JOINs
        assert "FROM m3u_channels m" in main_query_text
        assert "LEFT JOIN epg_channels e" in main_query_text
        assert "LEFT JOIN (" in main_query_text  # Programs subquery
        assert "GROUP BY source, channel_id" in main_query_text
