"""Tests for filter_passed_channels function."""

import pytest
from unittest.mock import patch

from common.file_generators import filter_passed_channels


class TestFilterPassedChannels:
    """Test suite for filter_passed_channels function."""

    def test_empty_input(self):
        """Test with empty channel list."""
        result = filter_passed_channels([])
        assert result == []

    def test_all_channels_passed(self):
        """Test when all channels have empty filter_reasons."""
        channels = [
            {"name": "Channel 1", "filter_reasons": "[]"},
            {"name": "Channel 2", "filter_reasons": []},
            {"name": "Channel 3", "filter_reasons": None}
        ]
        
        result = filter_passed_channels(channels)
        assert len(result) == 3
        assert result == channels

    def test_all_channels_filtered(self):
        """Test when all channels have filter reasons."""
        channels = [
            {"name": "Channel 1", "filter_reasons": '["rule1"]'},
            {"name": "Channel 2", "filter_reasons": ["rule2"]},
            {"name": "Channel 3", "filter_reasons": '["rule1", "rule2"]'}
        ]
        
        result = filter_passed_channels(channels)
        assert result == []

    def test_mixed_filter_states(self):
        """Test mix of passed and filtered channels."""
        channels = [
            {"name": "Channel 1", "filter_reasons": "[]"},
            {"name": "Channel 2", "filter_reasons": '["blocked"]'},
            {"name": "Channel 3", "filter_reasons": []},
            {"name": "Channel 4", "filter_reasons": '["rule1", "rule2"]'},
            {"name": "Channel 5", "filter_reasons": None}
        ]
        
        result = filter_passed_channels(channels)
        expected = [
            {"name": "Channel 1", "filter_reasons": "[]"},
            {"name": "Channel 3", "filter_reasons": []},
            {"name": "Channel 5", "filter_reasons": None}
        ]
        assert result == expected

    def test_string_json_filter_reasons(self):
        """Test handling of filter_reasons as JSON strings."""
        channels = [
            {"name": "Channel 1", "filter_reasons": "[]"},
            {"name": "Channel 2", "filter_reasons": '["rule1"]'},
            {"name": "Channel 3", "filter_reasons": '["rule1", "rule2"]'},
            {"name": "Channel 4", "filter_reasons": ""}
        ]
        
        result = filter_passed_channels(channels)
        expected = [
            {"name": "Channel 1", "filter_reasons": "[]"},
            {"name": "Channel 4", "filter_reasons": ""}  # Empty string treated as empty list
        ]
        assert result == expected

    def test_list_filter_reasons(self):
        """Test handling of filter_reasons as actual lists."""
        channels = [
            {"name": "Channel 1", "filter_reasons": []},
            {"name": "Channel 2", "filter_reasons": ["rule1"]},
            {"name": "Channel 3", "filter_reasons": ["rule1", "rule2"]},
            {"name": "Channel 4", "filter_reasons": None}
        ]
        
        result = filter_passed_channels(channels)
        expected = [
            {"name": "Channel 1", "filter_reasons": []},
            {"name": "Channel 4", "filter_reasons": None}
        ]
        assert result == expected

    def test_invalid_json_filter_reasons(self):
        """Test handling of invalid JSON in filter_reasons."""
        channels = [
            {"name": "Channel 1", "filter_reasons": "[]"},
            {"name": "Channel 2", "filter_reasons": "invalid json"},
            {"name": "Channel 3", "filter_reasons": '["rule1"'},  # Malformed JSON
            {"name": "Channel 4", "filter_reasons": "null"}
        ]
        
        result = filter_passed_channels(channels)
        expected = [
            {"name": "Channel 1", "filter_reasons": "[]"},
            {"name": "Channel 4", "filter_reasons": "null"}  # Valid JSON null
        ]
        assert result == expected

    def test_missing_filter_reasons_field(self):
        """Test handling of channels without filter_reasons field."""
        channels = [
            {"name": "Channel 1"},  # Missing filter_reasons
            {"name": "Channel 2", "filter_reasons": "[]"},
            {"name": "Channel 3", "other_field": "value"}  # Missing filter_reasons
        ]
        
        result = filter_passed_channels(channels)
        expected = [
            {"name": "Channel 1"},  # Default empty list passes
            {"name": "Channel 2", "filter_reasons": "[]"},
            {"name": "Channel 3", "other_field": "value"}  # Default empty list passes
        ]
        assert result == expected

    @pytest.mark.parametrize("filter_reasons,expected_pass", [
        ("[]", True),
        ([], True),
        (None, True),
        ("", True),
        ('["rule1"]', False),
        (["rule1"], False),
        ('["rule1", "rule2"]', False),
        (["rule1", "rule2"], False),
        ("null", True),  # JSON null
        ("invalid", False),  # Invalid JSON treated as non-empty
        ('{"key": "value"}', False),  # Object treated as non-empty
    ])
    def test_filter_reasons_variations(self, filter_reasons, expected_pass):
        """Test various filter_reasons formats."""
        channel = {"name": "Test Channel", "filter_reasons": filter_reasons}
        result = filter_passed_channels([channel])
        
        if expected_pass:
            assert len(result) == 1
            assert result[0] == channel
        else:
            assert len(result) == 0

    def test_preserves_channel_data(self):
        """Test that all channel data is preserved in filtered results."""
        channels = [
            {
                "name": "Channel 1",
                "tvg_id": "ch1",
                "stream_url": "http://example.com/stream1",
                "group": "Sports",
                "logo_url": "http://example.com/logo1.png",
                "filter_reasons": "[]"
            },
            {
                "name": "Channel 2",
                "tvg_id": "ch2",
                "stream_url": "http://example.com/stream2",
                "group": "News",
                "filter_reasons": '["blocked"]'
            }
        ]
        
        result = filter_passed_channels(channels)
        assert len(result) == 1
        assert result[0] == channels[0]  # All data preserved

    def test_large_dataset_performance(self):
        """Test performance with large number of channels."""
        # Create 1000 channels with mixed filter states
        channels = []
        for i in range(1000):
            filter_reasons = "[]" if i % 2 == 0 else '["blocked"]'
            channels.append({
                "name": f"Channel {i}",
                "tvg_id": f"ch{i}",
                "filter_reasons": filter_reasons
            })
        
        result = filter_passed_channels(channels)
        
        # Should have 500 passed channels (every even index)
        assert len(result) == 500
        assert all(int(ch["name"].split()[1]) % 2 == 0 for ch in result)
