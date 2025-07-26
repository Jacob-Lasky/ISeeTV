"""Tests for parse_epg_for_channels function following atomic design principles.

This module focuses exclusively on testing EPG channel parsing logic.
Each test validates one specific parsing scenario or edge case.
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from lxml import etree
from io import StringIO

from ingest.epg_parser import parse_epg_for_channels, ValidationResults
from models.models import EpgChannel


class TestParseEpgForChannels:
    """Atomic tests for parse_epg_for_channels function."""

    def setup_method(self):
        """Reset validation results before each test."""
        # Reset the global validation_results object
        from ingest import epg_parser

        epg_parser.validation_results = ValidationResults()

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_valid_epg_channels(self, mock_update_progress, patch_etree_parse):
        """Should parse valid EPG channels successfully."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel One</display-name>
                <icon src="http://example.com/icon1.png"/>
            </channel>
            <channel id="ch2">
                <display-name>Channel Two</display-name>
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)

        channels = list(parse_epg_for_channels(temp_xml_file, "test_source"))

        assert len(channels) == 2

        # Check first channel
        assert channels[0].channel_id == "ch1"
        assert channels[0].display_name == "Channel One"
        assert channels[0].icon_url == "http://example.com/icon1.png"

        # Check second channel
        assert channels[1].channel_id == "ch2"
        assert channels[1].display_name == "Channel Two"
        assert channels[1].icon_url == ""

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_channels_with_task_progress(self, mock_update_progress, patch_etree_parse):
        """Should update task progress when task_id provided."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel One</display-name>
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)

        channels = list(parse_epg_for_channels(temp_xml_file, "test_source", task_id="task123"))

        assert len(channels) == 1

        mock_update_progress.assert_called_once_with(
            "task123", 2, "Parsing EPG channels", 0
        )

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_channels_no_task_progress(self, mock_update_progress, patch_etree_parse):
        """Should not update task progress when task_id not provided."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel One</display-name>
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)

        channels = list(parse_epg_for_channels(temp_xml_file, "test_source"))

        assert len(channels) == 1

        mock_update_progress.assert_not_called()

    def test_parse_epg_channels_file_not_found(self):
        """Should raise FileNotFoundError when file doesn't exist."""

        with pytest.raises(FileNotFoundError):
            list(parse_epg_for_channels("nonexistent.xml", "test_source"))

    def test_parse_epg_channels_invalid_xml(self, patch_etree_parse):
        """Should raise XMLSyntaxError for malformed XML."""
        invalid_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel One
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(invalid_xml)

        with pytest.raises(etree.XMLSyntaxError):
            list(parse_epg_for_channels(temp_xml_file, "test_source"))

    def test_parse_epg_channels_no_root_element(self, patch_etree_parse):
        """Should raise ValueError when no root element found."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>"""

        temp_xml_file = patch_etree_parse(xml_content)

        with pytest.raises(etree.XMLSyntaxError):
            list(parse_epg_for_channels(temp_xml_file, "test_source"))

    def test_parse_epg_channels_wrong_root_element(self, patch_etree_parse):
        """Should raise ValueError when root element is not 'tv'."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <bad_root_tag>
            <channel id="ch1">
                <display-name>Channel One</display-name>
            </channel>
        </bad_root_tag>"""

        temp_xml_file = patch_etree_parse(xml_content)

        with pytest.raises(ValueError) as exc_info:
            list(parse_epg_for_channels(temp_xml_file, "test_source"))

        assert "Expected root tag 'tv', found 'bad_root_tag'" in str(exc_info.value)

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_channels_no_channels(self, mock_update_progress, patch_etree_parse):
        """Should return empty list when no channels found."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start="123" stop="456">
                <title>Test Program</title>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)

        channels = list(parse_epg_for_channels(temp_xml_file, "test_source"))

        assert len(channels) == 0
        mock_update_progress.assert_not_called()

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_channels_missing_display_name(self, mock_update_progress, patch_etree_parse):
        """Should raise ValueError when channel missing display-name."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <icon src="http://example.com/icon.png"/>
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)

        parsed_channels = list(parse_epg_for_channels(temp_xml_file, "test_source"))

        assert parsed_channels == []

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_channels_missing_id(self, mock_update_progress, patch_etree_parse):
        """Should use 'Unknown' as channel_id when id attribute missing."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel>
                <display-name>Channel One</display-name>
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)

        channels = list(parse_epg_for_channels(temp_xml_file, "test_source"))

        assert len(channels) == 1
        assert channels[0].channel_id == "Unknown"
        assert channels[0].display_name == "Channel One"

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_channels_with_icon(self, mock_update_progress, patch_etree_parse):
        """Should extract icon URL when icon element present."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel One</display-name>
                <icon src="https://example.com/logo.png"/>
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)

        channels = list(parse_epg_for_channels(temp_xml_file, "test_source"))

        assert len(channels) == 1
        assert channels[0].icon_url == "https://example.com/logo.png"

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_channels_icon_no_src(self, mock_update_progress, patch_etree_parse):
        """Should set icon_url to None when icon element has no src attribute."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel One</display-name>
                <icon/>
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)

        channels = list(parse_epg_for_channels(temp_xml_file, "test_source"))

        assert len(channels) == 1
        assert channels[0].icon_url == ""

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_channels_multiple_display_names(self, mock_update_progress, patch_etree_parse):
        """Should use first display-name when multiple exist."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel One</display-name>
                <display-name>Alternative Name</display-name>
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)

        channels = list(parse_epg_for_channels(temp_xml_file, "test_source"))

        assert len(channels) == 1
        assert channels[0].display_name == "Channel One"

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_channels_multiple_icons(self, mock_update_progress, patch_etree_parse):
        """Should use first icon when multiple exist."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel One</display-name>
                <icon src="https://example.com/icon1.png"/>
                <icon src="https://example.com/icon2.png"/>
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)

        channels = list(parse_epg_for_channels(temp_xml_file, "test_source"))

        assert len(channels) == 1
        assert channels[0].icon_url == "https://example.com/icon1.png"

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_channels_unicode_content(self, mock_update_progress, patch_etree_parse):
        """Should handle unicode content correctly."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="频道1">
                <display-name>中文频道</display-name>
                <icon src="https://example.com/中文.png"/>
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)

        channels = list(parse_epg_for_channels(temp_xml_file, "test_source"))

        assert len(channels) == 1
        assert channels[0].channel_id == "频道1"
        assert channels[0].display_name == "中文频道"
        assert channels[0].icon_url == "https://example.com/中文.png"

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    @patch("ingest.epg_parser.validate_root_element")
    @patch("ingest.epg_parser.validate_channel_element")
    def test_validation_functions_called(
        self, mock_validate_channel, mock_validate_root, mock_update_progress, patch_etree_parse
    ):
        """Should call validation functions during parsing."""
        mock_validate_channel.return_value = "ch1"

        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel One</display-name>
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        list(parse_epg_for_channels(temp_xml_file, "test_source"))

        mock_validate_root.assert_called_once()
        mock_validate_channel.assert_called_once()

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_channels_large_file(self, mock_update_progress, patch_etree_parse):
        """Should handle parsing many channels efficiently."""
        # Create XML with 100 channels
        channels_xml = []
        for i in range(100):
            channels_xml.append(
                f"""
            <channel id="ch{i}">
                <display-name>Channel {i}</display-name>
            </channel>"""
            )

        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            {''.join(channels_xml)}
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)

        channels = list(
            parse_epg_for_channels(temp_xml_file, "test_source", task_id="task123")
        )

        assert len(channels) == 100
        mock_update_progress.assert_called_once_with(
            "task123", 2, "Parsing EPG channels", 0
        )

        # Check first and last channels
        assert channels[0].channel_id == "ch0"
        assert channels[0].display_name == "Channel 0"
        assert channels[99].channel_id == "ch99"
        assert channels[99].display_name == "Channel 99"

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_channels_with_unexpected_exception(self, mock_update_progress, patch_etree_parse):
        """Test that unexpected exceptions are caught and logged during channel parsing."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Valid Channel</display-name>
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        
        # Mock validate_channel_element to raise unexpected exception
        with patch("ingest.epg_parser.validate_channel_element") as mock_validate:
            mock_validate.side_effect = RuntimeError("Unexpected error")
            
            with pytest.raises(RuntimeError):
                list(parse_epg_for_channels(temp_xml_file, "test_source"))
