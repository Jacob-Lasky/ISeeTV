"""Tests for get_streams_internal function following atomic design principles."""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime

from common.streams_utils import get_streams_internal
from models.stream_models import StreamChannel, StreamsResponse, StreamQueryParams


class TestGetStreamsInternal:
    """Atomic tests for get_streams_internal function."""
    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_basic_streams_internal_success(self, mock_filter_values_func, mock_filter_counts_func, 
                                          mock_streams_query, mock_session, mock_stream_channel, 
                                          mock_filter_counts, mock_filter_values):
        """Test basic get_streams_internal with successful response."""
        # Mock function returns
        mock_streams_query.return_value = ([mock_stream_channel], 100)
        mock_filter_counts_func.return_value = mock_filter_counts
        mock_filter_values_func.return_value = mock_filter_values

        # Create params object
        params = StreamQueryParams()

        # Call function with correct signature
        result = get_streams_internal(mock_session, "test_source", params)

        # Assertions
        assert result.success is True
        assert result.data == [mock_stream_channel]
        assert result.total == 100
        assert result.page == 1
        assert result.page_size == 100
        assert result.total_pages == 1
        assert result.has_next is False
        assert result.has_prev is False
        assert result.filters == mock_filter_values
        assert result.filter_view_counts == mock_filter_counts

        # Verify all functions were called with correct parameters
        mock_streams_query.assert_called_once_with(
            session=mock_session,
            source="test_source",
            group=None,
            global_filter=None,
            column_filters={},
            sort_field="name",
            sort_order="asc",
            page=1,
            page_size=100,
            apply_rules=True,
            filter_view="matched"
        )
        mock_filter_counts_func.assert_called_once_with(
            session=mock_session,
            source="test_source",
            group=None,
            global_filter=None,
            column_filters={}
        )
        mock_filter_values_func.assert_called_once_with(
            mock_session,
            "test_source"
        )

    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_with_all_parameters(self, mock_filter_values_func, mock_filter_counts_func,
                                                mock_streams_query, mock_session, mock_stream_channel,
                                                mock_filter_counts, mock_filter_values):
        """Test get_streams_internal with all parameters specified."""
        mock_streams_query.return_value = ([mock_stream_channel], 75)
        mock_filter_counts_func.return_value = mock_filter_counts
        mock_filter_values_func.return_value = mock_filter_values

        column_filters = {"name": "test", "group": "Sports"}

        params = StreamQueryParams(
            source="test_source",
            group="Entertainment",
            global_filter="search_term",
            column_filters=json.dumps(column_filters),
            sort_field="tvg_id",
            sort_order="desc",
            page=2,
            page_size=25,
            apply_rules=False,
            filter_view="all"
        )
        result = get_streams_internal(mock_session, "test_source", params)

        assert isinstance(result, StreamsResponse)
        assert len(result.data) == 1
        assert result.total == 75

        # Verify parameters were passed correctly
        mock_streams_query.assert_called_once_with(
            session=mock_session,
            source="test_source",
            group="Entertainment",
            global_filter="search_term",
            column_filters=column_filters,
            sort_field="tvg_id",
            sort_order="desc",
            page=2,
            page_size=25,
            apply_rules=False,
            filter_view="all"
        )
        mock_filter_counts_func.assert_called_once_with(
            session=mock_session,
            source="test_source",
            group="Entertainment",
            global_filter="search_term",
            column_filters=column_filters
        )

    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_with_empty_results(self, mock_filter_values_func, mock_filter_counts_func,
                                               mock_streams_query, mock_session, mock_filter_counts, 
                                               mock_filter_values):
        """Test get_streams_internal with empty streams result."""
        mock_streams_query.return_value = ([], 0)
        mock_filter_counts_func.return_value = {"normal": 0, "inverse": 0, "all": 0}
        mock_filter_values_func.return_value = {}

        params = StreamQueryParams()
        result = get_streams_internal(mock_session, "test_source", params)

        assert isinstance(result, StreamsResponse)
        assert len(result.data) == 0
        assert result.data == []
        assert result.total == 0
        assert result.filter_view_counts == {"normal": 0, "inverse": 0, "all": 0}
        assert result.filters == {}

    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_with_multiple_streams(self, mock_filter_values_func, mock_filter_counts_func,
                                                  mock_streams_query, mock_session, mock_filter_counts,
                                                  mock_filter_values):
        """Test get_streams_internal with multiple streams."""
        # Create multiple mock streams
        stream1 = StreamChannel(
            m3u_id=1, source="source1", tvg_id="ch001", name="Channel 1",
            stream_url="http://example.com/stream1.m3u8", logo_url=None,
            group="Entertainment", stream_mode="live", epg_id=None,
            display_name=None, icon_url=None,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
            filter_reasons=[], program_count=0,
            next_program_title=None, next_program_start=None
        )
        stream2 = StreamChannel(
            m3u_id=2, source="source2", tvg_id="ch002", name="Channel 2",
            stream_url="http://example.com/stream2.m3u8", logo_url=None,
            group="Sports", stream_mode="live", epg_id=None,
            display_name=None, icon_url=None,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
            filter_reasons=[], program_count=0,
            next_program_title=None, next_program_start=None
        )

        mock_streams_query.return_value = ([stream1, stream2], 200)
        mock_filter_counts_func.return_value = mock_filter_counts
        mock_filter_values_func.return_value = mock_filter_values

        params = StreamQueryParams()
        result = get_streams_internal(mock_session, "test_source", params)

        assert isinstance(result, StreamsResponse)
        assert len(result.data) == 2
        assert result.data[0].name == "Channel 1"
        assert result.data[1].name == "Channel 2"
        assert result.total == 200

    @pytest.mark.parametrize("sort_field,sort_order", [
        ("name", "asc"),
        ("name", "desc"),
        ("tvg_id", "asc"),
        ("display_name", "desc"),
        ("group", "asc"),
        ("source", "desc"),
        ("created_at", "asc"),
        ("updated_at", "desc"),
    ])
    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_sorting_parameters(self, mock_filter_values_func, mock_filter_counts_func,
                                               mock_streams_query, mock_session, mock_stream_channel,
                                               mock_filter_counts, mock_filter_values,
                                               sort_field, sort_order):
        """Test get_streams_internal with various sorting parameters."""
        mock_streams_query.return_value = ([mock_stream_channel], 100)
        mock_filter_counts_func.return_value = mock_filter_counts
        mock_filter_values_func.return_value = mock_filter_values

        params = StreamQueryParams(
            sort_field=sort_field,
            sort_order=sort_order
        )
        result = get_streams_internal(mock_session, "test_source", params)

        assert isinstance(result, StreamsResponse)
        # Verify the streams query was called with correct parameters from StreamQueryParams
        mock_streams_query.assert_called_once_with(
            session=mock_session,
            source="test_source",
            group=None,
            page=1,
            page_size=100,
            sort_field=sort_field,
            sort_order=sort_order,
            global_filter=None,
            column_filters={},  # always parsed to dict
            apply_rules=True,
            filter_view="matched"
        )

    @pytest.mark.parametrize("page,page_size", [
        (1, 10),
        (2, 25),
        (5, 100),
        (10, 200),
    ])
    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_pagination_parameters(self, mock_filter_values_func, mock_filter_counts_func,
                                                  mock_streams_query, mock_session, mock_stream_channel,
                                                  mock_filter_counts, mock_filter_values,
                                                  page, page_size):
        """Test get_streams_internal with various pagination parameters."""
        mock_streams_query.return_value = ([mock_stream_channel], 1000)
        mock_filter_counts_func.return_value = mock_filter_counts
        mock_filter_values_func.return_value = mock_filter_values

        params = StreamQueryParams(
            page=page,
            page_size=page_size
        )
        result = get_streams_internal(mock_session, "test_source", params)

        assert isinstance(result, StreamsResponse)
        # Verify the streams query was called with correct parameters from StreamQueryParams
        mock_streams_query.assert_called_once_with(
            session=mock_session,
            source="test_source",
            group=None,
            page=page,
            page_size=page_size,
            sort_field="name",
            sort_order="asc",
            global_filter=None,
            column_filters={},  # always parsed to dict
            apply_rules=True,
            filter_view="matched"
        )

    @pytest.mark.parametrize("apply_rules,filter_view", [
        (True, "normal"),
        (True, "inverse"),
        (True, "all"),
        (False, "normal"),
        (False, "inverse"),
        (False, "all"),
    ])
    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_rules_filtering_parameters(self, mock_filter_values_func, mock_filter_counts_func,
                                                       mock_streams_query, mock_session, mock_stream_channel,
                                                       mock_filter_counts, mock_filter_values,
                                                       apply_rules, filter_view):
        """Test get_streams_internal with various rules filtering parameters."""
        mock_streams_query.return_value = ([mock_stream_channel], 100)
        mock_filter_counts_func.return_value = mock_filter_counts
        mock_filter_values_func.return_value = mock_filter_values

        params = StreamQueryParams(
            apply_rules=apply_rules,
            filter_view=filter_view
        )
        result = get_streams_internal(mock_session, "test_source", params)

        assert isinstance(result, StreamsResponse)
        # Verify the streams query was called with correct parameters from StreamQueryParams
        mock_streams_query.assert_called_once_with(
            session=mock_session,
            source="test_source",
            group=None,
            page=1,
            page_size=100,
            sort_field="name",
            sort_order="asc",
            global_filter=None,
            column_filters={},  # always parsed to dict
            apply_rules=apply_rules,
            filter_view=filter_view
        )

    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_with_column_filters(self, mock_filter_values_func, mock_filter_counts_func,
                                                mock_streams_query, mock_session, mock_stream_channel,
                                                mock_filter_counts, mock_filter_values):
        """Test get_streams_internal with column filters."""
        mock_streams_query.return_value = ([mock_stream_channel], 50)
        mock_filter_counts_func.return_value = mock_filter_counts
        mock_filter_values_func.return_value = mock_filter_values

        column_filters = {
            "name": "test_channel",
            "tvg_id": "ch001",
            "display_name": "display",
            "group": "Sports",
            "source": "provider1"
        }

        params = StreamQueryParams(column_filters=json.dumps(column_filters))
        result = get_streams_internal(mock_session, "test_source", params)

        assert isinstance(result, StreamsResponse)
        # Verify the streams query was called with correct parameters from StreamQueryParams
        mock_streams_query.assert_called_once_with(
            session=mock_session,
            source="test_source",
            group=None,
            page=1,
            page_size=100,
            sort_field="name",
            sort_order="asc",
            global_filter=None,
            column_filters=column_filters,  # parsed from JSON string
            apply_rules=True,
            filter_view="matched"
        )
        mock_filter_counts_func.assert_called_once_with(
            session=mock_session,
            source="test_source",
            group=None,
            global_filter=None,
            column_filters=column_filters  # parsed from JSON string
        )

    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_handles_streams_query_exception(self, mock_filter_values_func, mock_filter_counts_func,
                                                            mock_streams_query, mock_session):
        """Test that exceptions from get_streams_query are propagated."""
        mock_streams_query.side_effect = Exception("Database error in streams query")
        mock_filter_counts_func.return_value = {"normal": 0, "inverse": 0, "all": 0}
        mock_filter_values_func.return_value = {}

        params = StreamQueryParams()
        with pytest.raises(Exception, match="Database error in streams query"):
            get_streams_internal(mock_session, "test_source", params)

    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_handles_filter_counts_exception(self, mock_filter_values_func, mock_filter_counts_func,
                                                            mock_streams_query, mock_session, mock_stream_channel):
        """Test that exceptions from get_filter_view_counts are propagated."""
        mock_streams_query.return_value = ([mock_stream_channel], 100)
        mock_filter_counts_func.side_effect = Exception("Database error in filter counts")
        mock_filter_values_func.return_value = {}

        params = StreamQueryParams()
        with pytest.raises(Exception, match="Database error in filter counts"):
            get_streams_internal(mock_session, "test_source", params)

    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_handles_filter_values_exception(self, mock_filter_values_func, mock_filter_counts_func,
                                                            mock_streams_query, mock_session, mock_stream_channel,
                                                            mock_filter_counts):
        """Test that exceptions from get_streams_filter_values are propagated."""
        mock_streams_query.return_value = ([mock_stream_channel], 100)
        mock_filter_counts_func.return_value = mock_filter_counts
        mock_filter_values_func.side_effect = Exception("Database error in filter values")

        params = StreamQueryParams()
        with pytest.raises(Exception, match="Database error in filter values"):
            get_streams_internal(mock_session, "test_source", params)

    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_with_none_column_filters(self, mock_filter_values_func, mock_filter_counts_func,
                                                     mock_streams_query, mock_session, mock_stream_channel,
                                                     mock_filter_counts, mock_filter_values):
        """Test get_streams_internal with None column_filters parameter."""
        mock_streams_query.return_value = ([mock_stream_channel], 100)
        mock_filter_counts_func.return_value = mock_filter_counts
        mock_filter_values_func.return_value = mock_filter_values

        params = StreamQueryParams(column_filters=None)
        result = get_streams_internal(mock_session, "test_source", params)

        assert isinstance(result, StreamsResponse)
        # Verify the streams query was called with correct parameters from StreamQueryParams
        mock_streams_query.assert_called_once_with(
            session=mock_session,
            source="test_source",
            group=None,
            page=1,
            page_size=100,
            sort_field="name",
            sort_order="asc",
            global_filter=None,
            column_filters={},  # always parsed to dict
            apply_rules=True,
            filter_view="matched"
        )

    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_with_empty_column_filters(self, mock_filter_values_func, mock_filter_counts_func,
                                                      mock_streams_query, mock_session, mock_stream_channel,
                                                      mock_filter_counts, mock_filter_values):
        """Test get_streams_internal with empty column_filters dictionary."""
        mock_streams_query.return_value = ([mock_stream_channel], 100)
        mock_filter_counts_func.return_value = mock_filter_counts
        mock_filter_values_func.return_value = mock_filter_values

        params = StreamQueryParams(column_filters=json.dumps({}))
        result = get_streams_internal(mock_session, "test_source", params)

        assert isinstance(result, StreamsResponse)
        # Verify the streams query was called with correct parameters from StreamQueryParams
        mock_streams_query.assert_called_once_with(
            session=mock_session,
            source="test_source",
            group=None,
            page=1,
            page_size=100,
            sort_field="name",
            sort_order="asc",
            global_filter=None,
            column_filters={},  # parsed from JSON string
            apply_rules=True,
            filter_view="matched"
        )

    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_response_structure(self, mock_filter_values_func, mock_filter_counts_func,
                                               mock_streams_query, mock_session, mock_stream_channel,
                                               mock_filter_counts, mock_filter_values):
        """Test that the response structure is correct."""
        mock_streams_query.return_value = ([mock_stream_channel], 100)
        mock_filter_counts_func.return_value = mock_filter_counts
        mock_filter_values_func.return_value = mock_filter_values

        params = StreamQueryParams()
        result = get_streams_internal(mock_session, "test_source", params)

        # Verify response is StreamsResponse instance
        assert isinstance(result, StreamsResponse)
        
        # Verify all required fields are present
        assert hasattr(result, 'data')
        assert hasattr(result, 'total')
        assert hasattr(result, 'filter_view_counts')
        assert hasattr(result, 'filters')
        
        # Verify field types
        assert isinstance(result.data, list)
        assert isinstance(result.total, int)
        assert isinstance(result.filter_view_counts, dict)
        assert isinstance(result.filters, dict)

    def test_streams_internal_function_signature(self):
        """Test that the function has the expected signature."""
        import inspect
        from common.streams_utils import get_streams_internal
        
        sig = inspect.signature(get_streams_internal)
        params = list(sig.parameters.keys())
        
        expected_params = ["session", "source", "params"]
        
        assert params == expected_params

    @patch('common.streams_utils.get_streams_query')
    @patch('common.streams_utils.get_filter_view_counts')
    @patch('common.streams_utils.get_streams_filter_values')
    def test_streams_internal_page_size_validation(self, mock_filter_values_func, mock_filter_counts_func,
                                                  mock_streams_query, mock_session, mock_stream_channel,
                                                  mock_filter_counts, mock_filter_values):
        """Test page_size validation logic: min(page_size, 500) and default to 100 if < 1."""
        mock_streams_query.return_value = ([mock_stream_channel], 100)
        mock_filter_counts_func.return_value = mock_filter_counts
        mock_filter_values_func.return_value = mock_filter_values
        
        # Test case 2: page_size < 1 should default to 100
        params = StreamQueryParams(page_size=0)
        result = get_streams_internal(mock_session, "test_source", params)
        
        # Verify the streams query was called with page_size=100 (default)
        mock_streams_query.assert_called_with(
            session=mock_session,
            source="test_source",
            group=None,
            page=1,
            page_size=100,  # Should default to 100
            sort_field="name",
            sort_order="asc",
            global_filter=None,
            column_filters={},
            apply_rules=True,
            filter_view="matched"
        )
        assert result.page_size == 100
        
        # Reset mocks for next test
        mock_streams_query.reset_mock()
        
        # Test case 3: negative page_size should default to 100
        params = StreamQueryParams(page_size=-5)
        result = get_streams_internal(mock_session, "test_source", params)
        
        # Verify the streams query was called with page_size=100 (default)
        mock_streams_query.assert_called_with(
            session=mock_session,
            source="test_source",
            group=None,
            page=1,
            page_size=100,  # Should default to 100
            sort_field="name",
            sort_order="asc",
            global_filter=None,
            column_filters={},
            apply_rules=True,
            filter_view="matched"
        )
        assert result.page_size == 100
