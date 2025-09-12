"""Tests for generate_m3u_content function."""

import pytest
from unittest.mock import patch

from common.file_generators import generate_m3u_content


class TestGenerateM3uContent:
    """Test suite for generate_m3u_content function."""

    def test_empty_channels(self):
        """Test with empty channel list."""
        result = generate_m3u_content([])
        assert result == "#EXTM3U"

    def test_single_channel_minimal_data(self):
        """Test with single channel having minimal required data."""
        channels = [
            {
                "name": "Test Channel",
                "stream_url": "http://example.com/stream.m3u8"
            }
        ]
        
        result = generate_m3u_content(channels)
        expected = (
            "#EXTM3U\n"
            '#EXTINF:-1 tvg-name="Test Channel",Test Channel\n'
            "http://example.com/stream.m3u8"
        )
        assert result == expected

    def test_single_channel_full_data(self):
        """Test with single channel having all metadata."""
        channels = [
            {
                "name": "ESPN",
                "tvg_id": "espn.us",
                "stream_url": "http://example.com/espn.m3u8",
                "logo_url": "http://example.com/espn.png",
                "group": "Sports"
            }
        ]
        
        result = generate_m3u_content(channels)
        expected = (
            "#EXTM3U\n"
            '#EXTINF:-1 tvg-id="espn.us" tvg-name="ESPN" tvg-logo="http://example.com/espn.png" group-title="Sports",ESPN\n'
            "http://example.com/espn.m3u8"
        )
        assert result == expected

    def test_multiple_channels(self):
        """Test with multiple channels."""
        channels = [
            {
                "name": "ESPN",
                "tvg_id": "espn.us",
                "stream_url": "http://example.com/espn.m3u8",
                "group": "Sports"
            },
            {
                "name": "CNN",
                "tvg_id": "cnn.us",
                "stream_url": "http://example.com/cnn.m3u8",
                "logo_url": "http://example.com/cnn.png",
                "group": "News"
            }
        ]
        
        result = generate_m3u_content(channels)
        expected = (
            "#EXTM3U\n"
            '#EXTINF:-1 tvg-id="espn.us" tvg-name="ESPN" group-title="Sports",ESPN\n'
            "http://example.com/espn.m3u8\n"
            '#EXTINF:-1 tvg-id="cnn.us" tvg-name="CNN" tvg-logo="http://example.com/cnn.png" group-title="News",CNN\n'
            "http://example.com/cnn.m3u8"
        )
        assert result == expected

    def test_channel_missing_optional_fields(self):
        """Test channel with missing optional fields."""
        channels = [
            {
                "name": "Basic Channel",
                "stream_url": "http://example.com/basic.m3u8"
                # Missing tvg_id, logo_url, group
            }
        ]
        
        result = generate_m3u_content(channels)
        expected = (
            "#EXTM3U\n"
            '#EXTINF:-1 tvg-name="Basic Channel",Basic Channel\n'
            "http://example.com/basic.m3u8"
        )
        assert result == expected

    def test_channel_missing_name(self):
        """Test channel with missing name field."""
        channels = [
            {
                "tvg_id": "test.channel",
                "stream_url": "http://example.com/test.m3u8",
                "group": "Test"
                # Missing name
            }
        ]
        
        result = generate_m3u_content(channels)
        expected = (
            "#EXTM3U\n"
            '#EXTINF:-1 tvg-id="test.channel" group-title="Test"\n'
            "http://example.com/test.m3u8"
        )
        assert result == expected

    def test_channel_missing_stream_url(self):
        """Test channel with missing stream URL."""
        channels = [
            {
                "name": "No Stream Channel",
                "tvg_id": "nostream.channel"
                # Missing stream_url
            }
        ]
        
        result = generate_m3u_content(channels)
        expected = (
            "#EXTM3U\n"
            '#EXTINF:-1 tvg-id="nostream.channel" tvg-name="No Stream Channel",No Stream Channel'
        )
        assert result == expected

    def test_empty_string_fields(self):
        """Test channel with empty string fields."""
        channels = [
            {
                "name": "",
                "tvg_id": "",
                "stream_url": "",
                "logo_url": "",
                "group": ""
            }
        ]
        
        result = generate_m3u_content(channels)
        expected = "#EXTM3U\n#EXTINF:-1"
        assert result == expected

    def test_none_fields(self):
        """Test channel with None fields."""
        channels = [
            {
                "name": None,
                "tvg_id": None,
                "stream_url": None,
                "logo_url": None,
                "group": None
            }
        ]
        
        result = generate_m3u_content(channels)
        expected = "#EXTM3U\n#EXTINF:-1"
        assert result == expected

    def test_special_characters_in_metadata(self):
        """Test handling of special characters in channel metadata."""
        channels = [
            {
                "name": 'Channel "Special" & More',
                "tvg_id": "special.channel",
                "stream_url": "http://example.com/special.m3u8",
                "logo_url": "http://example.com/logo with spaces.png",
                "group": "Group & Category"
            }
        ]
        
        result = generate_m3u_content(channels)
        expected = (
            "#EXTM3U\n"
            '#EXTINF:-1 tvg-id="special.channel" tvg-name="Channel "Special" & More" '
            'tvg-logo="http://example.com/logo with spaces.png" group-title="Group & Category",'
            'Channel "Special" & More\n'
            "http://example.com/special.m3u8"
        )
        assert result == expected

    def test_unicode_characters(self):
        """Test handling of Unicode characters."""
        channels = [
            {
                "name": "Канал Россия",
                "tvg_id": "russia.tv",
                "stream_url": "http://example.com/russia.m3u8",
                "group": "Международные"
            }
        ]
        
        result = generate_m3u_content(channels)
        expected = (
            "#EXTM3U\n"
            '#EXTINF:-1 tvg-id="russia.tv" tvg-name="Канал Россия" group-title="Международные",Канал Россия\n'
            "http://example.com/russia.m3u8"
        )
        assert result == expected

    def test_long_urls_and_names(self):
        """Test handling of very long URLs and names."""
        long_name = "Very Long Channel Name " * 10
        long_url = "http://example.com/" + "very-long-path/" * 20 + "stream.m3u8"
        
        channels = [
            {
                "name": long_name,
                "tvg_id": "long.channel",
                "stream_url": long_url
            }
        ]
        
        result = generate_m3u_content(channels)
        assert "#EXTM3U" in result
        assert long_name in result
        assert long_url in result

    @pytest.mark.parametrize("field_name,field_value,expected_attr", [
        ("tvg_id", "test.id", 'tvg-id="test.id"'),
        ("name", "Test Name", 'tvg-name="Test Name"'),
        ("logo_url", "http://logo.png", 'tvg-logo="http://logo.png"'),
        ("group", "Test Group", 'group-title="Test Group"'),
    ])
    def test_individual_metadata_fields(self, field_name, field_value, expected_attr):
        """Test individual metadata field formatting."""
        channel = {
            "name": "Test Channel",
            "stream_url": "http://example.com/test.m3u8",
            field_name: field_value
        }
        
        result = generate_m3u_content([channel])
        assert expected_attr in result

    def test_large_playlist(self):
        """Test performance with large number of channels."""
        channels = []
        for i in range(1000):
            channels.append({
                "name": f"Channel {i}",
                "tvg_id": f"ch{i}",
                "stream_url": f"http://example.com/stream{i}.m3u8",
                "group": f"Group {i % 10}"
            })
        
        result = generate_m3u_content(channels)
        lines = result.split('\n')
        
        # Should have header + 2 lines per channel (EXTINF + URL)
        assert len(lines) == 1 + (1000 * 2)
        assert lines[0] == "#EXTM3U"
        
        # Check first and last channels
        assert "Channel 0" in lines[1]
        assert "Channel 999" in lines[-2]
