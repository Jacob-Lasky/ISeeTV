"""Tests for apply_unified_channel_filtering function."""

import pytest
from unittest.mock import patch

from common.file_generators import apply_unified_channel_filtering


class TestApplyUnifiedChannelFiltering:
    """Test suite for apply_unified_channel_filtering function."""

    def test_empty_inputs(self):
        """Test with empty input lists."""
        result = apply_unified_channel_filtering([], [], [])
        assert result == ([], [], [])

    def test_no_matching_channel_ids(self):
        """Test when M3U and EPG have no matching channel IDs."""
        m3u_channels = [
            {"tvg_id": "channel1", "name": "Channel 1", "filter_reasons": "[]"}
        ]
        epg_channels = [
            {"channel_id": "channel2", "display_name": "Channel 2", "filter_reasons": "[]"}
        ]
        programs = [
            {"channel_id": "channel2", "title": "Program 1", "filter_reasons": "[]"}
        ]

        result = apply_unified_channel_filtering(m3u_channels, epg_channels, programs)
        assert result == ([], [], [])

    def test_matching_channel_ids_all_passed(self):
        """Test when channels have matching IDs and all passed filtering."""
        m3u_channels = [
            {"tvg_id": "channel1", "name": "Channel 1", "filter_reasons": "[]"},
            {"tvg_id": "channel2", "name": "Channel 2", "filter_reasons": "[]"}
        ]
        epg_channels = [
            {"channel_id": "channel1", "display_name": "Channel 1", "filter_reasons": "[]"},
            {"channel_id": "channel3", "display_name": "Channel 3", "filter_reasons": "[]"}
        ]
        programs = [
            {"channel_id": "channel1", "title": "Program 1", "filter_reasons": "[]"},
            {"channel_id": "channel2", "title": "Program 2", "filter_reasons": "[]"},
            {"channel_id": "channel3", "title": "Program 3", "filter_reasons": "[]"}
        ]

        result = apply_unified_channel_filtering(m3u_channels, epg_channels, programs)
        
        # Only channel1 should remain (intersection of M3U and EPG)
        expected_m3u = [{"tvg_id": "channel1", "name": "Channel 1", "filter_reasons": "[]"}]
        expected_epg = [{"channel_id": "channel1", "display_name": "Channel 1", "filter_reasons": "[]"}]
        expected_programs = [{"channel_id": "channel1", "title": "Program 1", "filter_reasons": "[]"}]
        
        assert result == (expected_m3u, expected_epg, expected_programs)

    def test_filtered_channels_excluded(self):
        """Test that channels with filter reasons are excluded."""
        m3u_channels = [
            {"tvg_id": "channel1", "name": "Channel 1", "filter_reasons": "[]"},
            {"tvg_id": "channel2", "name": "Channel 2", "filter_reasons": '["blocked"]'}
        ]
        epg_channels = [
            {"channel_id": "channel1", "display_name": "Channel 1", "filter_reasons": "[]"},
            {"channel_id": "channel2", "display_name": "Channel 2", "filter_reasons": "[]"}
        ]
        programs = [
            {"channel_id": "channel1", "title": "Program 1", "filter_reasons": "[]"},
            {"channel_id": "channel2", "title": "Program 2", "filter_reasons": "[]"}
        ]

        result = apply_unified_channel_filtering(m3u_channels, epg_channels, programs)
        
        # Only channel1 should remain (channel2 filtered in M3U)
        expected_m3u = [{"tvg_id": "channel1", "name": "Channel 1", "filter_reasons": "[]"}]
        expected_epg = [{"channel_id": "channel1", "display_name": "Channel 1", "filter_reasons": "[]"}]
        expected_programs = [{"channel_id": "channel1", "title": "Program 1", "filter_reasons": "[]"}]
        
        assert result == (expected_m3u, expected_epg, expected_programs)

    def test_missing_channel_ids(self):
        """Test handling of channels with missing tvg_id/channel_id."""
        m3u_channels = [
            {"name": "Channel 1", "filter_reasons": "[]"},  # Missing tvg_id
            {"tvg_id": "channel2", "name": "Channel 2", "filter_reasons": "[]"}
        ]
        epg_channels = [
            {"display_name": "Channel 1", "filter_reasons": "[]"},  # Missing channel_id
            {"channel_id": "channel2", "display_name": "Channel 2", "filter_reasons": "[]"}
        ]
        programs = [
            {"channel_id": "channel2", "title": "Program 2", "filter_reasons": "[]"}
        ]

        result = apply_unified_channel_filtering(m3u_channels, epg_channels, programs)
        
        # Only channel2 should remain (has valid IDs in both)
        expected_m3u = [{"tvg_id": "channel2", "name": "Channel 2", "filter_reasons": "[]"}]
        expected_epg = [{"channel_id": "channel2", "display_name": "Channel 2", "filter_reasons": "[]"}]
        expected_programs = [{"channel_id": "channel2", "title": "Program 2", "filter_reasons": "[]"}]
        
        assert result == (expected_m3u, expected_epg, expected_programs)

    def test_complex_filtering_scenario(self):
        """Test complex scenario with multiple channels and various filter states."""
        m3u_channels = [
            {"tvg_id": "ch1", "name": "Channel 1", "filter_reasons": "[]"},
            {"tvg_id": "ch2", "name": "Channel 2", "filter_reasons": '["rule1"]'},
            {"tvg_id": "ch3", "name": "Channel 3", "filter_reasons": "[]"},
            {"tvg_id": "ch4", "name": "Channel 4", "filter_reasons": "[]"}
        ]
        epg_channels = [
            {"channel_id": "ch1", "display_name": "Channel 1", "filter_reasons": "[]"},
            {"channel_id": "ch2", "display_name": "Channel 2", "filter_reasons": "[]"},
            {"channel_id": "ch3", "display_name": "Channel 3", "filter_reasons": '["rule2"]'},
            {"channel_id": "ch5", "display_name": "Channel 5", "filter_reasons": "[]"}
        ]
        programs = [
            {"channel_id": "ch1", "title": "Program 1", "filter_reasons": "[]"},
            {"channel_id": "ch2", "title": "Program 2", "filter_reasons": "[]"},
            {"channel_id": "ch3", "title": "Program 3", "filter_reasons": "[]"},
            {"channel_id": "ch4", "title": "Program 4", "filter_reasons": "[]"},
            {"channel_id": "ch5", "title": "Program 5", "filter_reasons": '["rule3"]'}
        ]

        result = apply_unified_channel_filtering(m3u_channels, epg_channels, programs)
        
        # Only ch1 should remain (passed in both M3U and EPG, and exists in both)
        expected_m3u = [{"tvg_id": "ch1", "name": "Channel 1", "filter_reasons": "[]"}]
        expected_epg = [{"channel_id": "ch1", "display_name": "Channel 1", "filter_reasons": "[]"}]
        expected_programs = [{"channel_id": "ch1", "title": "Program 1", "filter_reasons": "[]"}]
        
        assert result == (expected_m3u, expected_epg, expected_programs)
