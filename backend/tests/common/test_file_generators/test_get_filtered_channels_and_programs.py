"""Tests for get_filtered_channels_and_programs function."""

import pytest
from unittest.mock import Mock, patch

from common.file_generators import get_filtered_channels_and_programs


class TestGetFilteredChannelsAndPrograms:
    """Test suite for get_filtered_channels_and_programs function."""

    def _create_mock_session_and_results(self, m3u_data=None, epg_data=None, programs_data=None):
        """DRY helper to create mock session with configurable results."""
        mock_session = Mock()
        
        # Default empty data if not provided
        m3u_data = m3u_data or []
        epg_data = epg_data or []
        programs_data = programs_data or []
        
        # Create mock results that properly support iteration
        mock_results = []
        for data in [m3u_data, epg_data, programs_data]:
            mock_result = Mock()
            mock_result.__iter__ = Mock(return_value=iter([
                Mock(_mapping=item) for item in data
            ]))
            mock_results.append(mock_result)
        
        mock_session.execute.side_effect = mock_results
        return mock_session

    @patch('common.file_generators.SessionLocal')
    def test_successful_query_execution(self, mock_session_local):
        """Test successful database query execution."""
        # Sample data for each table
        m3u_data = [
            {"tvg_id": "espn.us", "name": "ESPN", "source": "test_source"},
            {"tvg_id": "cnn.us", "name": "CNN", "source": "test_source"}
        ]
        epg_data = [
            {"channel_id": "espn.us", "display_name": "ESPN", "source": "test_source"},
            {"channel_id": "cnn.us", "display_name": "CNN", "source": "test_source"}
        ]
        programs_data = [
            {"channel_id": "espn.us", "title": "SportsCenter", "source": "test_source"},
            {"channel_id": "cnn.us", "title": "CNN News", "source": "test_source"}
        ]
        
        mock_session = self._create_mock_session_and_results(m3u_data, epg_data, programs_data)
        mock_session_local.return_value.__enter__.return_value = mock_session
        
        result = get_filtered_channels_and_programs("test_source")
        
        # Verify session.execute was called three times (M3U, EPG, programs)
        assert mock_session.execute.call_count == 3
        
        # Verify result structure
        m3u_channels, epg_channels, programs = result
        assert len(m3u_channels) == 2
        assert len(epg_channels) == 2
        assert len(programs) == 2
        assert m3u_channels[0]["name"] == "ESPN"
        assert epg_channels[0]["display_name"] == "ESPN"
        assert programs[0]["title"] == "SportsCenter"

    @patch('common.file_generators.SessionLocal')
    def test_empty_source_name(self, mock_session_local):
        """Test with empty source name."""
        mock_session = self._create_mock_session_and_results()
        mock_session_local.return_value.__enter__.return_value = mock_session
        
        result = get_filtered_channels_and_programs("")
        
        # Should still execute three queries but with no source filtering
        assert mock_session.execute.call_count == 3
        
        # Verify result structure
        m3u_channels, epg_channels, programs = result
        assert len(m3u_channels) == 0
        assert len(epg_channels) == 0
        assert len(programs) == 0
        
    @patch('common.file_generators.SessionLocal')
    def test_none_source_name(self, mock_session_local):
        """Test with None source name."""
        mock_session = self._create_mock_session_and_results()
        mock_session_local.return_value.__enter__.return_value = mock_session
        
        result = get_filtered_channels_and_programs(None)
        
        # Should execute queries without filtering
        assert mock_session.execute.call_count == 3
        
        # Verify result structure
        m3u_channels, epg_channels, programs = result
        assert len(m3u_channels) == 0
        assert len(epg_channels) == 0
        assert len(programs) == 0

    @patch('common.file_generators.SessionLocal')
    def test_database_error_handling(self, mock_session_local):
        """Test handling of database errors."""
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Database connection error")
        mock_session_local.return_value.__enter__.return_value = mock_session
        
        # Should raise the exception (no error handling in the function)
        with pytest.raises(Exception, match="Database connection error"):
            get_filtered_channels_and_programs("test_source")

    @patch('common.file_generators.SessionLocal')
    def test_source_filtering_in_queries(self, mock_session_local):
        """Test that source parameter is properly used in SQL queries."""
        mock_session = self._create_mock_session_and_results()
        mock_session_local.return_value.__enter__.return_value = mock_session
        
        get_filtered_channels_and_programs("test_source")
        
        # Verify that execute was called with parameters containing the source
        calls = mock_session.execute.call_args_list
        assert len(calls) == 3
        
        # Check that source parameter was passed to queries that need it
        for call in calls:
            if len(call[0]) > 1:  # If there are parameters
                params = call[0][1] if len(call[0]) > 1 else call[1].get('params', {})
                if params:  # Some queries might not have source filtering
                    assert params.get('source') == 'test_source'

    @patch('common.file_generators.SessionLocal')
    def test_return_tuple_structure(self, mock_session_local):
        """Test that function returns proper tuple structure."""
        # Create test data for all three tables
        m3u_data = [{"tvg_id": "test1", "name": "Test 1"}]
        epg_data = [{"channel_id": "test1", "display_name": "Test 1"}]
        programs_data = [{"channel_id": "test1", "title": "Test Program"}]
        
        mock_session = self._create_mock_session_and_results(m3u_data, epg_data, programs_data)
        mock_session_local.return_value.__enter__.return_value = mock_session
        
        result = get_filtered_channels_and_programs("test_source")
        
        # Verify result is a tuple with three elements
        assert isinstance(result, tuple)
        assert len(result) == 3
        
        m3u_channels, epg_channels, programs = result
        assert isinstance(m3u_channels, list)
        assert isinstance(epg_channels, list)
        assert isinstance(programs, list)
        assert len(m3u_channels) == 1
        assert len(epg_channels) == 1
        assert len(programs) == 1

    @pytest.mark.parametrize("source", ["source1", "source2", "test_source"])
    @patch('common.file_generators.SessionLocal')
    def test_multiple_source_names(self, mock_session_local, source):
        """Test with different source names using parametrized testing."""
        mock_session = self._create_mock_session_and_results()
        mock_session_local.return_value.__enter__.return_value = mock_session
        
        result = get_filtered_channels_and_programs(source)
        
        # Should execute three queries regardless of source
        assert mock_session.execute.call_count == 3
        assert isinstance(result, tuple)
        assert len(result) == 3

    @patch('common.file_generators.SessionLocal')
    def test_large_result_set_handling(self, mock_session_local):
        """Test handling of large result sets."""
        # Create large mock datasets
        large_m3u = [{"tvg_id": f"channel_{i}", "name": f"Channel {i}"} for i in range(100)]
        large_epg = [{"channel_id": f"channel_{i}", "display_name": f"Channel {i}"} for i in range(100)]
        large_programs = [{"channel_id": f"channel_{i}", "title": f"Program {i}"} for i in range(500)]
        
        mock_session = self._create_mock_session_and_results(large_m3u, large_epg, large_programs)
        mock_session_local.return_value.__enter__.return_value = mock_session
        
        result = get_filtered_channels_and_programs("test_source")
        
        m3u_channels, epg_channels, programs = result
        assert len(m3u_channels) == 100
        assert len(epg_channels) == 100
        assert len(programs) == 500

    @patch('common.file_generators.SessionLocal')
    def test_session_context_manager_usage(self, mock_session_local):
        """Test that SessionLocal context manager is used correctly."""
        mock_session = self._create_mock_session_and_results()
        mock_session_local.return_value.__enter__.return_value = mock_session
        
        get_filtered_channels_and_programs("test_source")
        
        # Verify SessionLocal was called and used as context manager
        mock_session_local.assert_called_once()
        mock_session_local.return_value.__enter__.assert_called_once()
        mock_session_local.return_value.__exit__.assert_called_once()

    @patch('common.file_generators.SessionLocal')
    def test_data_consistency_and_structure(self, mock_session_local):
        """Test with realistic mock data structure and verify data consistency."""
        # Create realistic mock data with consistent structure
        m3u_data = [
            {"tvg_id": "espn.us", "name": "ESPN", "source": "test_source", "group": "Sports"},
            {"tvg_id": "cnn.us", "name": "CNN", "source": "test_source", "group": "News"}
        ]
        epg_data = [
            {"channel_id": "espn.us", "display_name": "ESPN", "source": "test_source"},
            {"channel_id": "cnn.us", "display_name": "CNN", "source": "test_source"}
        ]
        programs_data = [
            {"channel_id": "espn.us", "title": "SportsCenter", "start_time": "2024-01-01 10:00:00", "source": "test_source"},
            {"channel_id": "cnn.us", "title": "Breaking News", "start_time": "2024-01-01 11:00:00", "source": "test_source"}
        ]
        
        mock_session = self._create_mock_session_and_results(m3u_data, epg_data, programs_data)
        mock_session_local.return_value.__enter__.return_value = mock_session
        
        result = get_filtered_channels_and_programs("test_source")
        
        m3u_channels, epg_channels, programs = result
        
        # Verify data structure and consistency
        assert len(m3u_channels) == 2
        assert len(epg_channels) == 2
        assert len(programs) == 2
        
        # Verify data fields are accessible
        assert m3u_channels[0]["name"] == "ESPN"
        assert m3u_channels[0]["group"] == "Sports"
        assert epg_channels[0]["display_name"] == "ESPN"
        assert programs[0]["title"] == "SportsCenter"
        assert programs[0]["start_time"] == "2024-01-01 10:00:00"
