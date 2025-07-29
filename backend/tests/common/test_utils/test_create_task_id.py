"""
Tests for create_task_id function from common.utils.

Following atomic design principles:
- Single responsibility: Tests only create_task_id function
- Pure functions: Each test validates one specific behavior
- No side effects: Tests are isolated and independent
"""

import datetime as dt
from unittest.mock import patch
import pytest
import time

from common.utils import create_task_id


class TestCreateTaskId:
    """Test class for create_task_id function."""

    @pytest.mark.parametrize(
        "source_name,file_type,task_type,expected_prefix",
        [
            ("test_source", "m3u", "download", "download_m3u_test_source_"),
            ("another_source", "epg", "ingest", "ingest_epg_another_source_"),
            ("source-with-dashes", "m3u", "ingest", "ingest_m3u_source-with-dashes_"),
            (
                "source_with_underscores",
                "epg",
                "download",
                "download_epg_source_with_underscores_",
            ),
        ],
    )
    def test_create_task_id_format(
        self, source_name, file_type, task_type, expected_prefix
    ):
        """Test that task ID has correct format with all parameter combinations."""
        with patch("common.utils.dt.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240127_143022"

            result = create_task_id(source_name, file_type, task_type)

            expected = f"{expected_prefix}20240127_143022"
            assert result == expected
            mock_datetime.now.assert_called_once()
            mock_datetime.now.return_value.strftime.assert_called_once_with(
                "%Y%m%d_%H%M%S"
            )

    def test_create_task_id_timestamp_format(self):
        """Test that timestamp format is correct."""
        # Use a real datetime to verify format
        result = create_task_id("test", "m3u", "download")

        # Extract timestamp part (last 15 characters)
        timestamp_part = result[-15:]

        # Verify timestamp format: YYYYMMDD_HHMMSS
        assert len(timestamp_part) == 15
        assert timestamp_part[8] == "_"

        # Verify it's a valid datetime format
        try:
            dt.datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")
        except ValueError:
            pytest.fail("Timestamp format is invalid")

    def test_create_task_id_uniqueness(self):
        """Test that consecutive calls produce different task IDs."""
        result1 = create_task_id("test", "m3u", "download")
        time.sleep(1)
        result2 = create_task_id("test", "m3u", "download")

        # Should be different due to timestamp
        assert result1 != result2

    @pytest.mark.parametrize(
        "source_name",
        [
            "simple",
            "with-dashes",
            "with_underscores",
            "with.dots",
            "MixedCase",
            "123numeric",
            "special!@#chars",
            "",  # Edge case: empty string
        ],
    )
    def test_create_task_id_source_name_handling(self, source_name):
        """Test that various source name formats are handled correctly."""
        with patch("common.utils.dt.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240127_143022"

            result = create_task_id(source_name, "m3u", "download")

            expected = f"download_m3u_{source_name}_20240127_143022"
            assert result == expected

    def test_create_task_id_literal_types(self):
        """Test that function accepts only valid literal types."""
        # Valid combinations should work
        result = create_task_id("test", "m3u", "download")
        assert isinstance(result, str)

        result = create_task_id("test", "epg", "ingest")
        assert isinstance(result, str)

        # Note: Invalid literal types would be caught by type checker,
        # not at runtime, so we don't test invalid combinations here
