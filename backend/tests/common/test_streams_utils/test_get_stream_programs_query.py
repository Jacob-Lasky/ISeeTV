"""Tests for get_stream_programs_query function following atomic design principles."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from common.streams_utils import get_stream_programs_query
from models.stream_models import StreamProgram


class TestGetStreamProgramsQuery:
    """Atomic tests for get_stream_programs_query function."""

    @pytest.fixture
    def mock_program_row(self):
        """Mock database row with all required program fields for StreamProgram validation."""
        # Create a simple object with attributes that match StreamProgram model expectations
        class MockRow:
            def __init__(self):
                # Required fields for StreamProgram
                self.program_id = 1
                self.source = "test_source"
                self.program_uid = "prog_001"
                self.channel_id = "ch001"
                self.start_time = datetime(2024, 1, 1, 20, 0, 0)
                self.end_time = datetime(2024, 1, 1, 21, 0, 0)
                self.title = "Test Program"
                self.description = "Test program description"
                
                # Channel context fields (joined data)
                self.channel_name = "Test Channel"
                self.channel_display_name = "Test Channel Display"
                self.channel_group = "Entertainment"
                self.stream_url = "http://example.com/stream.m3u8"
                self.logo_url = "http://example.com/logo.png"
                self.icon_url = "http://example.com/program_icon.png"
                
                # Metadata
                self.created_at = datetime(2024, 1, 1, 12, 0, 0)
                self.updated_at = datetime(2024, 1, 1, 13, 0, 0)
        
        return MockRow()

    @pytest.fixture
    def mock_count_row(self):
        """Mock count query result."""
        mock_row = Mock()
        mock_row.total = 50
        return mock_row

    def test_basic_programs_query_no_filters(self, mock_session, mock_program_row, mock_count_row):
        """Test basic programs query with no filters applied."""
        # Mock count query result
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        # Mock main query result
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_program_row]))
        
        # Configure session to return different results for count vs main query
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        programs, total_count = get_stream_programs_query(mock_session, "ch001", "test_source")

        assert total_count == 50
        assert len(programs) == 1
        assert isinstance(programs[0], StreamProgram)
        assert programs[0].title == "Test Program"
        assert programs[0].source == "test_source"
        assert programs[0].channel_id == "ch001"

    def test_programs_query_with_required_parameters(self, mock_session, mock_program_row, mock_count_row):
        """Test that source and channel_id parameters are properly applied."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_program_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        programs, total_count = get_stream_programs_query(mock_session, "my_channel", "my_source")

        assert total_count == 50
        assert len(programs) == 1
        
        # Verify source and channel_id filters are applied in both queries
        assert mock_session.execute.call_count == 2
        for call in mock_session.execute.call_args_list:
            query_text = call[0][0].text
            params = call[0][1]
            assert "source = :source" in query_text
            assert "channel_id = :channel_id" in query_text
            assert params["source"] == "my_source"
            assert params["channel_id"] == "my_channel"

    def test_programs_query_with_global_filter(self, mock_session, mock_program_row, mock_count_row):
        """Test programs query with global search filter applied."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_program_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        programs, total_count = get_stream_programs_query(
            mock_session, 
            "ch001", 
            "test_source", 
            global_filter="news"
        )

        assert total_count == 50
        assert len(programs) == 1
        
        # Verify global filter is applied
        for call in mock_session.execute.call_args_list:
            query_text = call[0][0].text
            params = call[0][1]
            assert "p.title LIKE :global_filter" in query_text
            assert "p.description LIKE :global_filter" in query_text
            assert "m.name LIKE :global_filter" in query_text
            assert "e.display_name LIKE :global_filter" in query_text
            assert params["global_filter"] == "%news%"

    def test_programs_query_with_column_filters(self, mock_session, mock_program_row, mock_count_row):
        """Test programs query with column-specific filters applied."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_program_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        column_filters = {
            "title": "news",
            "description": "program"
        }

        programs, total_count = get_stream_programs_query(
            mock_session, 
            "test_source", 
            "ch001",
            column_filters=column_filters
        )

        assert total_count == 50
        assert len(programs) == 1
        
        # Verify column filters are applied
        for call in mock_session.execute.call_args_list:
            query_text = call[0][0].text
            params = call[0][1]
            assert "p.title LIKE :title_filter" in query_text
            assert "p.description LIKE :description_filter" in query_text
            assert params["title_filter"] == "%news%"
            assert params["description_filter"] == "%program%"

    @pytest.mark.parametrize("sort_field,sort_order,expected_field,expected_order", [
        ("title", "asc", "title", "ASC"),
        ("title", "desc", "title", "DESC"),
        ("start_time", "asc", "start_time", "ASC"),
        ("start_time", "desc", "start_time", "DESC"),
        ("end_time", "asc", "end_time", "ASC"),
        ("end_time", "desc", "end_time", "DESC"),
        ("created_at", "desc", "created_at", "DESC"),
        ("updated_at", "asc", "updated_at", "ASC"),
    ])
    def test_programs_query_sorting(self, mock_session, mock_program_row, mock_count_row,
                                  sort_field, sort_order, expected_field, expected_order):
        """Test programs query with various sorting options."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_program_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        programs, total_count = get_stream_programs_query(
            mock_session, 
            "test_source", 
            "ch001",
            sort_field=sort_field, 
            sort_order=sort_order
        )

        assert total_count == 50
        assert len(programs) == 1
        
        # Verify sorting is applied in main query (second call)
        main_query_call = mock_session.execute.call_args_list[1]
        query_text = main_query_call[0][0].text
        expected_order_by = f"ORDER BY p.{expected_field} {expected_order}"
        assert expected_order_by in query_text

    def test_programs_query_invalid_sort_field_defaults_to_start_time(self, mock_session, mock_program_row, mock_count_row):
        """Test that invalid sort field defaults to 'start_time'."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_program_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        programs, total_count = get_stream_programs_query(
            mock_session, 
            "test_source", 
            "ch001",
            sort_field="invalid_field"
        )

        assert total_count == 50
        assert len(programs) == 1
        
        # Verify default sorting is applied
        main_query_call = mock_session.execute.call_args_list[1]
        query_text = main_query_call[0][0].text
        assert "ORDER BY p.start_time ASC" in query_text

    def test_programs_query_invalid_sort_order_defaults_to_asc(self, mock_session, mock_program_row, mock_count_row):
        """Test that invalid sort order defaults to 'asc'."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_program_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        programs, total_count = get_stream_programs_query(
            mock_session, 
            "test_source", 
            "ch001",
            sort_order="invalid_order"
        )

        assert total_count == 50
        assert len(programs) == 1
        
        # Verify default sort order is applied
        main_query_call = mock_session.execute.call_args_list[1]
        query_text = main_query_call[0][0].text
        assert "ORDER BY p.start_time ASC" in query_text

    def test_programs_query_pagination(self, mock_session, mock_program_row, mock_count_row):
        """Test programs query pagination parameters."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_program_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        programs, total_count = get_stream_programs_query(
            mock_session, 
            "test_source", 
            "ch001",
            page=3, 
            page_size=25
        )

        assert total_count == 50
        assert len(programs) == 1
        
        # Verify pagination parameters
        main_query_call = mock_session.execute.call_args_list[1]
        query_text = main_query_call[0][0].text
        params = main_query_call[0][1]
        
        assert "LIMIT :limit OFFSET :offset" in query_text
        assert params["limit"] == 25
        assert params["offset"] == 50  # (page-1) * page_size = (3-1) * 25 = 50

    def test_programs_query_datetime_conversion_string_input(self, mock_session, mock_count_row):
        """Test datetime conversion when database returns string dates."""
        # Create proper mock row with string datetime values and all required StreamProgram fields
        class MockRow:
            def __init__(self):
                # Required fields for StreamProgram
                self.program_id = 1
                self.source = "test_source"
                self.program_uid = "prog_001"
                self.channel_id = "ch001"
                self.start_time = "2024-01-01T20:00:00"  # String for conversion testing
                self.end_time = "2024-01-01T21:00:00"    # String for conversion testing
                self.title = "Test Program"
                self.description = "Test program description"
                
                # Channel context fields (joined data)
                self.channel_name = "Test Channel"
                self.channel_display_name = "Test Channel Display"
                self.channel_group = "Entertainment"
                self.stream_url = "http://example.com/stream.m3u8"
                self.logo_url = "http://example.com/logo.png"
                self.icon_url = "http://example.com/program_icon.png"
                
                # Metadata (strings for conversion testing)
                self.created_at = "2024-01-01T12:00:00"
                self.updated_at = "2024-01-01T13:00:00"
        
        mock_row = MockRow()
        
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        programs, total_count = get_stream_programs_query(mock_session, "ch001", "test_source")

        assert len(programs) == 1
        program = programs[0]
        
        # Verify datetime conversion
        assert isinstance(program.start_time, datetime)
        assert isinstance(program.end_time, datetime)
        assert isinstance(program.created_at, datetime)
        assert isinstance(program.updated_at, datetime)
        assert program.start_time.year == 2024
        assert program.start_time.month == 1
        assert program.start_time.day == 1
        assert program.start_time.hour == 20

    def test_programs_query_datetime_conversion_datetime_input(self, mock_session, mock_count_row):
        """Test datetime handling when database returns datetime objects."""
        start_dt = datetime(2024, 1, 1, 20, 0, 0)
        end_dt = datetime(2024, 1, 1, 21, 0, 0)
        created_dt = datetime(2024, 1, 1, 12, 0, 0)
        updated_dt = datetime(2024, 1, 1, 13, 0, 0)
        
        # Create proper mock row with all required StreamProgram fields
        class MockRow:
            def __init__(self):
                # Required fields for StreamProgram
                self.program_id = 1
                self.source = "test_source"
                self.program_uid = "prog_001"
                self.channel_id = "ch001"
                self.start_time = start_dt
                self.end_time = end_dt
                self.title = "Test Program"
                self.description = "Test program description"
                
                # Channel context fields (joined data)
                self.channel_name = "Test Channel"
                self.channel_display_name = "Test Channel Display"
                self.channel_group = "Entertainment"
                self.stream_url = "http://example.com/stream.m3u8"
                self.logo_url = "http://example.com/logo.png"
                self.icon_url = "http://example.com/program_icon.png"
                
                # Metadata
                self.created_at = created_dt
                self.updated_at = updated_dt
        
        mock_row = MockRow()
        
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        programs, total_count = get_stream_programs_query(mock_session, "ch001", "test_source")

        assert len(programs) == 1
        program = programs[0]
        
        # Verify datetime objects are preserved
        assert program.start_time == start_dt
        assert program.end_time == end_dt
        assert program.created_at == created_dt
        assert program.updated_at == updated_dt

    def test_programs_query_handles_null_values(self, mock_session, mock_count_row):
        """Test programs query handles null/None values correctly."""
        # Create proper mock row with null values and all required StreamProgram fields
        class MockRow:
            def __init__(self):
                # Required fields for StreamProgram
                self.program_id = 1
                self.source = "test_source"
                self.program_uid = "prog_001"
                self.channel_id = "ch001"
                self.start_time = datetime(2024, 1, 1, 20, 0, 0)
                self.end_time = datetime(2024, 1, 1, 21, 0, 0)
                self.title = "Test Program"
                self.description = None  # Testing null value
                
                # Channel context fields (some null for testing)
                self.channel_name = "Test Channel"
                self.channel_display_name = None  # Testing null value
                self.channel_group = None  # Testing null value
                self.stream_url = "http://example.com/stream.m3u8"
                self.logo_url = None  # Testing null value
                self.icon_url = None  # Testing null value
                
                # Metadata
                self.created_at = datetime(2024, 1, 1, 12, 0, 0)
                self.updated_at = datetime(2024, 1, 1, 13, 0, 0)
        
        mock_row = MockRow()
        
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        programs, total_count = get_stream_programs_query(mock_session, "ch001", "test_source")

        assert len(programs) == 1
        program = programs[0]
        
        # Verify null values are handled correctly
        assert program.description is None
        assert program.icon_url is None

    def test_programs_query_handles_database_exception(self, mock_session):
        """Test that database exceptions are propagated."""
        mock_session.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            get_stream_programs_query(mock_session, "ch001", "test_source")

    def test_programs_query_empty_result(self, mock_session, mock_count_row):
        """Test programs query with empty result set."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        programs, total_count = get_stream_programs_query(mock_session, "ch001", "test_source")

        assert total_count == 50
        assert len(programs) == 0
        assert programs == []

    def test_programs_query_ignores_empty_column_filter_values(self, mock_session, mock_program_row, mock_count_row):
        """Test that empty column filter values are ignored."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_program_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        column_filters = {
            "title": "valid_title",
            "description": "",  # Empty string should be ignored
        }

        programs, total_count = get_stream_programs_query(
            mock_session,
            "test_source",
            "ch001",
            column_filters=column_filters
        )

        assert total_count == 50
        assert len(programs) == 1
        
        # Verify only non-empty filters are included
        for call in mock_session.execute.call_args_list:
            query_text = call[0][0].text
            params = call[0][1]
            
            assert "p.title LIKE :title_filter" in query_text
            # Empty description filter should not appear in query
            assert "description_filter" not in params
            
            assert params["title_filter"] == "%valid_title%"

    def test_programs_query_ignores_invalid_column_filters(self, mock_session, mock_program_row, mock_count_row):
        """Test that invalid column filter keys are ignored."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_program_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        column_filters = {
            "title": "valid",
            "invalid_column": "ignored",
            "another_invalid": "also_ignored"
        }

        programs, total_count = get_stream_programs_query(
            mock_session, 
            "test_source", 
            "ch001",
            column_filters=column_filters
        )

        assert total_count == 50
        assert len(programs) == 1
        
        # Verify only valid column filter is included
        for call in mock_session.execute.call_args_list:
            query_text = call[0][0].text
            params = call[0][1]
            
            assert "title LIKE :title_filter" in query_text
            assert "invalid_column" not in query_text
            assert "another_invalid" not in query_text
            assert params["title_filter"] == "%valid%"

    def test_programs_query_with_all_filters_combined(self, mock_session, mock_program_row, mock_count_row):
        """Test programs query with all filter types combined."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_program_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        column_filters = {"title": "test", "category": "News"}

        programs, total_count = get_stream_programs_query(
            mock_session,
            "test_source",
            "ch001",
            global_filter="search_term",
            column_filters=column_filters,
            sort_field="title",
            sort_order="desc",
            page=2,
            page_size=10
        )

        assert total_count == 50
        assert len(programs) == 1

    def test_sql_query_structure(self, mock_session, mock_program_row, mock_count_row):
        """Test that the generated SQL query has the expected structure."""
        mock_count_result = Mock()
        mock_count_result.fetchone.return_value = mock_count_row
        
        mock_main_result = Mock()
        mock_main_result.__iter__ = Mock(return_value=iter([mock_program_row]))
        
        mock_session.execute.side_effect = [mock_count_result, mock_main_result]

        get_stream_programs_query(mock_session, "test_source", "ch001")

        # Verify count query structure
        count_query_call = mock_session.execute.call_args_list[0]
        count_query_text = count_query_call[0][0].text
        assert "SELECT COUNT(*) as total" in count_query_text
        assert "FROM programs" in count_query_text
        
        # Verify main query structure
        main_query_call = mock_session.execute.call_args_list[1]
        main_query_text = main_query_call[0][0].text
        
        # Check for expected SELECT fields
        expected_fields = [
            "program_id",
            "source",
            "program_uid",
            "channel_id",
            "start_time",
            "end_time",
            "title",
            "description",
            "created_at",
            "updated_at",
            "channel_name",
            "channel_display_name",
            "channel_group",
            "stream_url",
            "logo_url",
            "icon_url"
        ]
        
        for field in expected_fields:
            assert field in main_query_text
        
        # Check for expected table
        assert "FROM programs" in main_query_text
