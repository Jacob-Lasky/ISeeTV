"""Tests for generate_epg_content function."""

import pytest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from common.file_generators import generate_epg_content


class TestGenerateEpgContent:
    """Test suite for generate_epg_content function."""

    def test_empty_inputs(self):
        """Test with empty channels and programs."""
        result = generate_epg_content([], [])
        
        # Parse XML to verify structure
        lines = result.split('\n')
        assert '<?xml version="1.0" encoding="utf-8" ?>' in lines[0]
        assert '<!DOCTYPE tv SYSTEM "xmltv.dtd">' in lines[0]
        
        # Find the TV element line
        tv_line = None
        for line in lines:
            if '<tv' in line and 'generator-info-name="IPTV"' in line:
                tv_line = line
                break
        assert tv_line is not None

    def test_channels_only_no_programs(self):
        """Test with channels but no programs."""
        channels = [
            {
                "channel_id": "espn.us",
                "display_name": "ESPN",
                "icon_url": "http://example.com/espn.png"
            }
        ]
        
        result = generate_epg_content(channels, [])
        
        # Verify channel is included
        assert 'id="espn.us"' in result
        assert '<display-name>ESPN</display-name>' in result
        assert 'src="http://example.com/espn.png"' in result

    def test_programs_only_no_channels(self):
        """Test with programs but no channels."""
        programs = [
            {
                "channel_id": "espn.us",
                "title": "SportsCenter",
                "description": "Sports news and highlights",
                "start_time": "2024-01-01T12:00:00",
                "end_time": "2024-01-01T13:00:00"
            }
        ]
        
        result = generate_epg_content([], programs)
        
        # Programs should be filtered out since no valid channels
        assert 'SportsCenter' not in result
        assert 'programme' not in result

    def test_single_channel_with_programs(self):
        """Test with single channel and its programs."""
        channels = [
            {
                "channel_id": "espn.us",
                "display_name": "ESPN"
            }
        ]
        programs = [
            {
                "channel_id": "espn.us",
                "title": "SportsCenter",
                "description": "Sports news",
                "start_time": "2024-01-01T12:00:00",
                "end_time": "2024-01-01T13:00:00"
            }
        ]
        
        result = generate_epg_content(channels, programs)
        
        # Verify channel
        assert 'id="espn.us"' in result
        assert '<display-name>ESPN</display-name>' in result
        
        # Verify program
        assert 'channel="espn.us"' in result
        assert '<title>SportsCenter</title>' in result
        assert '<desc>Sports news</desc>' in result
        assert 'start="20240101120000 +0000"' in result
        assert 'stop="20240101130000 +0000"' in result

    def test_multiple_channels_and_programs(self):
        """Test with multiple channels and programs."""
        channels = [
            {"channel_id": "espn.us", "display_name": "ESPN"},
            {"channel_id": "cnn.us", "display_name": "CNN", "icon_url": "http://cnn.png"}
        ]
        programs = [
            {
                "channel_id": "espn.us",
                "title": "SportsCenter",
                "description": "Sports news",
                "start_time": "2024-01-01T12:00:00",
                "end_time": "2024-01-01T13:00:00"
            },
            {
                "channel_id": "cnn.us",
                "title": "CNN News",
                "description": "Breaking news",
                "start_time": "2024-01-01T12:00:00",
                "end_time": "2024-01-01T12:30:00"
            }
        ]
        
        result = generate_epg_content(channels, programs)
        
        # Verify both channels
        assert 'id="espn.us"' in result
        assert 'id="cnn.us"' in result
        assert '<display-name>ESPN</display-name>' in result
        assert '<display-name>CNN</display-name>' in result
        
        # Verify both programs
        assert '<title>SportsCenter</title>' in result
        assert '<title>CNN News</title>' in result

    def test_programs_filtered_by_valid_channels(self):
        """Test that programs are filtered to only include valid channel IDs."""
        channels = [
            {"channel_id": "espn.us", "display_name": "ESPN"}
        ]
        programs = [
            {
                "channel_id": "espn.us",
                "title": "Valid Program",
                "description": "This should appear",
                "start_time": "2024-01-01T12:00:00",
                "end_time": "2024-01-01T13:00:00"
            },
            {
                "channel_id": "invalid.channel",
                "title": "Invalid Program",
                "description": "This should not appear",
                "start_time": "2024-01-01T12:00:00",
                "end_time": "2024-01-01T13:00:00"
            }
        ]
        
        result = generate_epg_content(channels, programs)
        
        # Only valid program should appear
        assert 'Valid Program' in result
        assert 'Invalid Program' not in result

    def test_channel_missing_optional_fields(self):
        """Test channel with missing optional fields."""
        channels = [
            {
                "channel_id": "basic.channel"
                # Missing display_name and icon_url
            }
        ]
        
        result = generate_epg_content(channels, [])
        
        # Channel should still be included with ID
        assert 'id="basic.channel"' in result
        # No display-name or icon elements should be present for this channel
        channel_section = result[result.find('id="basic.channel"'):result.find('</channel>')]
        assert '<display-name>' not in channel_section
        assert '<icon' not in channel_section

    def test_program_missing_optional_fields(self):
        """Test program with missing optional fields."""
        channels = [{"channel_id": "test.channel", "display_name": "Test"}]
        programs = [
            {
                "channel_id": "test.channel",
                "title": "Basic Program"
                # Missing description, start_time, end_time
            }
        ]
        
        result = generate_epg_content(channels, programs)
        
        # Program should be included with available data
        assert '<title>Basic Program</title>' in result
        # Empty description can be either <desc></desc> or <desc/> - both are valid XML
        assert ('<desc></desc>' in result or '<desc/>' in result)
        # No start/stop attributes should be present
        programme_section = result[result.find('Basic Program'):result.find('</programme>')]
        assert 'start=' not in programme_section
        assert 'stop=' not in programme_section

    def test_none_fields(self):
        """Test handling of None fields."""
        channels = [
            {
                "channel_id": "test.channel",
                "display_name": None,
                "icon_url": None
            }
        ]
        programs = [
            {
                "channel_id": "test.channel",
                "title": None,
                "description": None,
                "start_time": None,
                "end_time": None
            }
        ]
        
        result = generate_epg_content(channels, programs)
        
        # Should handle None values gracefully
        assert 'id="test.channel"' in result

    def test_special_characters_in_content(self):
        """Test handling of special characters in content."""
        channels = [
            {
                "channel_id": "special.channel",
                "display_name": 'Channel "Special" & More'
            }
        ]
        programs = [
            {
                "channel_id": "special.channel",
                "title": 'Show "Title" & Description',
                "description": "Description with <tags> & special chars"
            }
        ]
        
        result = generate_epg_content(channels, programs)
        
        # XML should be properly escaped
        assert 'Channel "Special" &amp; More' in result or 'Channel &quot;Special&quot; &amp; More' in result
        assert 'Show "Title" &amp; Description' in result or 'Show &quot;Title&quot; &amp; Description' in result

    def test_unicode_characters(self):
        """Test handling of Unicode characters."""
        channels = [
            {
                "channel_id": "unicode.channel",
                "display_name": "Канал Россия"
            }
        ]
        programs = [
            {
                "channel_id": "unicode.channel",
                "title": "Новости",
                "description": "Последние новости"
            }
        ]
        
        result = generate_epg_content(channels, programs)
        
        # Unicode should be preserved
        assert "Канал Россия" in result
        assert "Новости" in result
        assert "Последние новости" in result

    def test_datetime_formatting(self):
        """Test proper datetime formatting for EPG."""
        channels = [{"channel_id": "test.channel", "display_name": "Test"}]
        programs = [
            {
                "channel_id": "test.channel",
                "title": "Test Program",
                "start_time": "2024-01-01T12:30:45",
                "end_time": "2024-01-01T13:45:30"
            }
        ]
        
        result = generate_epg_content(channels, programs)
        
        # Should format as YYYYMMDDHHMMSS +0000
        assert 'start="20240101123045 +0000"' in result
        assert 'stop="20240101134530 +0000"' in result

    def test_timestamp_attributes(self):
        """Test that timestamp attributes are included."""
        channels = [{"channel_id": "test.channel", "display_name": "Test"}]
        programs = [
            {
                "channel_id": "test.channel",
                "title": "Test Program",
                "start_time": "2024-01-01T12:00:00",
                "end_time": "2024-01-01T13:00:00"
            }
        ]
        
        result = generate_epg_content(channels, programs)
        
        # Should include timestamp attributes
        assert 'start_timestamp=' in result
        assert 'stop_timestamp=' in result

    def test_xml_structure_validity(self):
        """Test that generated XML has valid structure."""
        channels = [{"channel_id": "test.channel", "display_name": "Test"}]
        programs = [
            {
                "channel_id": "test.channel",
                "title": "Test Program",
                "description": "Test description"
            }
        ]
        
        result = generate_epg_content(channels, programs)
        
        # Should be parseable XML (remove DOCTYPE for parsing)
        xml_content = result.split('\n', 1)[1]  # Remove first line with DOCTYPE
        try:
            # Parse without the DOCTYPE declaration
            clean_xml = xml_content.replace('<!DOCTYPE tv SYSTEM "xmltv.dtd">', '')
            root = ET.fromstring(clean_xml)
            assert root.tag == 'tv'
            assert root.get('generator-info-name') == 'IPTV'
        except ET.ParseError:
            pytest.fail("Generated XML is not valid")

    def test_large_dataset(self):
        """Test performance with large number of channels and programs."""
        channels = []
        programs = []
        
        # Create 100 channels
        for i in range(100):
            channels.append({
                "channel_id": f"channel{i}",
                "display_name": f"Channel {i}"
            })
            
            # Create 10 programs per channel
            for j in range(10):
                programs.append({
                    "channel_id": f"channel{i}",
                    "title": f"Program {j} on Channel {i}",
                    "description": f"Description for program {j}",
                    "start_time": f"2024-01-01T{j:02d}:00:00",
                    "end_time": f"2024-01-01T{j+1:02d}:00:00"
                })
        
        result = generate_epg_content(channels, programs)
        
        # Should include all channels and programs
        assert result.count('<channel') == 100
        assert result.count('<programme') == 1000
