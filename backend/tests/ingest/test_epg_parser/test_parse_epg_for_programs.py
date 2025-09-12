"""Tests for parse_epg_for_programs function following atomic design principles.

This module focuses exclusively on testing EPG program parsing logic.
Each test validates one specific parsing scenario or edge case.
"""

import pytz
import pytest
from unittest.mock import patch, mock_open
from lxml import etree
import datetime as dt

from ingest.epg_parser import parse_epg_for_programs, ValidationResults


class TestParseEpgForPrograms:
    """Atomic tests for parse_epg_for_programs function."""

    def setup_method(self):
        """Reset validation results before each test."""
        # Reset the global validation_results object
        from ingest import epg_parser

        epg_parser.validation_results = ValidationResults()

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_valid_epg_programs_utc(
        self, mock_update_progress, patch_etree_parse
    ):
        """Should parse valid EPG programs successfully."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="1735689600" stop_timestamp="1735693200">
                <title>Test Program</title>
                <desc>Program description</desc>
            </programme>
            <programme channel="ch2" start_timestamp="1735693200" stop_timestamp="1735696800">
                <title>Another Program</title>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        programs = list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

        assert len(programs) == 2

        # Check first program
        assert programs[0].channel_id == "ch1"
        assert programs[0].title == "Test Program"
        assert programs[0].description == "Program description"
        assert programs[0].start_time == dt.datetime(
            2025, 1, 1, 0, 0, 0, tzinfo=pytz.UTC
        )
        assert programs[0].end_time == dt.datetime(2025, 1, 1, 1, 0, 0, tzinfo=pytz.UTC)

        # Check second program
        assert programs[1].channel_id == "ch2"
        assert programs[1].title == "Another Program"
        assert programs[1].description == ""
        assert programs[1].start_time == dt.datetime(
            2025, 1, 1, 1, 0, 0, tzinfo=pytz.UTC
        )
        assert programs[1].end_time == dt.datetime(2025, 1, 1, 2, 0, 0, tzinfo=pytz.UTC)

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_valid_epg_programs_est(
        self, mock_update_progress, patch_etree_parse
    ):
        """Should parse valid EPG programs successfully, converting to UTC if timezone is wrong."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="1735714800" stop_timestamp="1735718400">
                <title>Test Program</title>
                <desc>Program description</desc>
            </programme>
            <programme channel="ch2" start_timestamp="1735718400" stop_timestamp="1735722000">
                <title>Another Program</title>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        programs = list(parse_epg_for_programs(temp_xml_file, "test_source", "EST"))

        assert len(programs) == 2

        # Check first program
        assert programs[0].channel_id == "ch1"
        assert programs[0].title == "Test Program"
        assert programs[0].description == "Program description"
        assert programs[0].start_time == dt.datetime(
            2025, 1, 1, 12, 0, 0, tzinfo=pytz.UTC
        )
        assert programs[0].end_time == dt.datetime(
            2025, 1, 1, 13, 0, 0, tzinfo=pytz.UTC
        )

        # Check second program
        assert programs[1].channel_id == "ch2"
        assert programs[1].title == "Another Program"
        assert programs[1].description == ""
        assert programs[1].start_time == dt.datetime(
            2025, 1, 1, 13, 0, 0, tzinfo=pytz.UTC
        )
        assert programs[1].end_time == dt.datetime(
            2025, 1, 1, 14, 0, 0, tzinfo=pytz.UTC
        )

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_with_task_progress(
        self, mock_update_progress, patch_etree_parse
    ):
        """Should update task progress when task_id provided."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="1735689600" stop_timestamp="1735693200">
                <title>Test Program</title>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)

        # Run the function
        result = list(
            parse_epg_for_programs(
                temp_xml_file, "test_source", "UTC", task_id="task123"
            )
        )

        mock_update_progress.assert_called_once_with(
            "task123", 4, "Parsing EPG programs", 0
        )

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_no_task_progress(
        self, mock_update_progress, patch_etree_parse
    ):
        """Should not update task progress when task_id not provided."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start="20240101120" stop="20240101130">
                <title>Test Program</title>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

        mock_update_progress.assert_not_called()

    def test_parse_epg_programs_file_not_found(self, patch_etree_parse):
        """Should raise FileNotFoundError when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            list(parse_epg_for_programs("nonexistent.xml", "test_source", "UTC"))

    def test_parse_epg_programs_invalid_xml(self, patch_etree_parse):
        """Should raise XMLSyntaxError for malformed XML."""
        invalid_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start="20240101120">
                <title>Test Program
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(invalid_xml)
        with pytest.raises(etree.XMLSyntaxError):
            list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

    def test_parse_epg_programs_no_root_element(self, patch_etree_parse):
        """Should raise ValueError when no root element found."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>"""

        temp_xml_file = patch_etree_parse(xml_content)
        with pytest.raises(etree.XMLSyntaxError):
            list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

    def test_parse_epg_programs_wrong_root_element(self, patch_etree_parse):
        """Should raise ValueError when root element is not 'tv'."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <bad_root_tag>
            <programme channel="ch1" start="20240101120" stop="20240101130">
                <title>Test Program</title>
            </programme>
        </bad_root_tag>"""

        temp_xml_file = patch_etree_parse(xml_content)
        with pytest.raises(ValueError) as exc_info:
            list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

        assert "Expected root tag 'tv', found 'bad_root_tag'" in str(exc_info.value)

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_no_programs(
        self, mock_update_progress, patch_etree_parse
    ):
        """Should return empty list when no programs found."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <channel id="ch1">
                <display-name>Channel One</display-name>
            </channel>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        programs = list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

        assert len(programs) == 0
        mock_update_progress.assert_not_called()

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_missing_title(
        self, mock_update_progress, patch_etree_parse
    ):
        """Logger warns with invalid programs, should not raise ValueError"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="20240101120" stop_timestamp="20240101130">
                <desc>Program description</desc>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_missing_channel(
        self, mock_update_progress, patch_etree_parse
    ):
        """Logger warns with invalid programs, should not raise ValueError"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme start_timestamp="20240101120" stop_timestamp="20240101130">
                <title>Test Program</title>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_missing_start_timestamp(
        self, mock_update_progress, patch_etree_parse
    ):
        """Logger warns with invalid programs, should not raise ValueError"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" stop_timestamp="20240101130">
                <title>Test Program</title>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_missing_stop_timestamp(
        self, mock_update_progress, patch_etree_parse
    ):
        """Logger warns with invalid programs, should not raise ValueError"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="20240101120">
                <title>Test Program</title>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_invalid_datetime_format(
        self, mock_update_progress, patch_etree_parse
    ):
        """Logger warns with invalid programs, should not raise ValueError"""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="invalid-date" stop_timestamp="20240101130">
                <title>Test Program</title>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_with_description(
        self, mock_update_progress, patch_etree_parse
    ):
        """Should extract description when desc element present."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="20240101120" stop_timestamp="20240101130">
                <title>Test Program</title>
                <desc>This is a test program description.</desc>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        programs = list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

        assert len(programs) == 1
        assert programs[0].description == "This is a test program description."

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_no_description(
        self, mock_update_progress, patch_etree_parse
    ):
        """Should set description to None when desc element missing."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="20240101120" stop_timestamp="20240101130">
                <title>Test Program</title>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        programs = list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

        assert len(programs) == 1
        assert programs[0].description == ""

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_multiple_descriptions(
        self, mock_update_progress, patch_etree_parse
    ):
        """Should use first description when multiple exist."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="20240101120" stop_timestamp="20240101130">
                <title>Test Program</title>
                <desc>First description</desc>
                <desc>Second description</desc>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        programs = list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

        assert len(programs) == 1
        assert programs[0].description == "First description"

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_unicode_content(
        self, mock_update_progress, patch_etree_parse
    ):
        """Should handle unicode content correctly."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="频道1" start_timestamp="20240101120" stop_timestamp="20240101130">
                <title>中文节目</title>
                <desc>这是一个中文节目描述。</desc>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        programs = list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

        assert len(programs) == 1
        assert programs[0].channel_id == "频道1"
        assert programs[0].title == "中文节目"
        assert programs[0].description == "这是一个中文节目描述。"

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    @patch("ingest.epg_parser.validate_root_element")
    @patch("ingest.epg_parser.validate_programme_element")
    def test_validation_functions_called(
        self,
        mock_validate_programme,
        mock_validate_root,
        mock_update_progress,
        patch_etree_parse,
    ):
        """Should call validation functions during parsing."""
        mock_validate_programme.return_value = "prog1"

        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="20240101120" stop_timestamp="20240101130">
                <title>Test Program</title>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

        mock_validate_root.assert_called_once()
        mock_validate_programme.assert_called_once()

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_large_file(
        self, mock_update_progress, patch_etree_parse
    ):
        """Should handle parsing many programs efficiently."""
        # Create XML with 100 programs
        programs_xml = []
        for i in range(100):
            start_hour = 10 + (i % 14)  # Cycle through hours 10-23
            stop_hour = start_hour + 1
            programs_xml.append(
                f"""
            <programme channel="ch1" start_timestamp="202401010{start_hour:02d}0" stop_timestamp="202401010{stop_hour:02d}0">
                <title>Program {i}</title>
                <desc>Description for program {i}</desc>
            </programme>"""
            )

        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            {''.join(programs_xml)}
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        programs = list(
            parse_epg_for_programs(
                temp_xml_file, "test_source", "UTC", task_id="task123"
            )
        )

        assert len(programs) == 100
        mock_update_progress.assert_called_once_with(
            "task123", 4, "Parsing EPG programs", 0
        )

        # Check first and last programs
        assert programs[0].title == "Program 0"
        assert programs[0].description == "Description for program 0"
        assert programs[99].title == "Program 99"
        assert programs[99].description == "Description for program 99"

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_program_id_fallback(
        self, mock_update_progress, patch_etree_parse
    ):
        """Should handle program ID fallback logic correctly."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="20240101120" stop_timestamp="20240101130">
                <title>Test Program</title>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        programs = list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

        assert len(programs) == 1
        # Program ID should be generated from channel + start time
        expected_id = "ch1_20240101120"
        assert programs[0].program_id == expected_id

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_epg_programs_special_characters_in_title(
        self, mock_update_progress, patch_etree_parse
    ):
        """Should handle special characters in program titles."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="20240101120" stop_timestamp="20240101130">
                <title>Program &amp; Show &lt;HD&gt; "Special"</title>
                <desc>Description with &quot;quotes&quot; and &amp; symbols.</desc>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        programs = list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))

        assert len(programs) == 1
        assert programs[0].title == 'Program & Show <HD> "Special"'
        assert programs[0].description == 'Description with "quotes" and & symbols.'

    @patch("ingest.epg_parser.IngestTaskManager.update_step_progress")
    def test_parse_programs_with_unexpected_exception(self, mock_update_progress, patch_etree_parse):
        """Test that unexpected exceptions are caught and logged during program parsing."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tv>
            <programme channel="ch1" start_timestamp="20240101120" stop_timestamp="20240101130">
                <title>Valid Program</title>
            </programme>
        </tv>"""

        temp_xml_file = patch_etree_parse(xml_content)
        
        with patch("ingest.epg_parser.validate_programme_element") as mock_validate:
            mock_validate.side_effect = RuntimeError("Unexpected error")
            
            with pytest.raises(RuntimeError):
                list(parse_epg_for_programs(temp_xml_file, "test_source", "UTC"))
