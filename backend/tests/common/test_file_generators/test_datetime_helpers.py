"""Tests for datetime helper functions."""

import pytest
from datetime import datetime

from common.file_generators import _format_epg_datetime, _datetime_to_timestamp


class TestFormatEpgDatetime:
    """Test suite for _format_epg_datetime function."""

    def test_valid_datetime_string(self):
        """Test formatting valid datetime string."""
        result = _format_epg_datetime("2024-01-01T12:30:45")
        assert result == "20240101123045 +0000"

    def test_different_date_formats(self):
        """Test various valid date formats."""
        test_cases = [
            ("2024-12-31T23:59:59", "20241231235959 +0000"),
            ("2024-01-01T00:00:00", "20240101000000 +0000"),
            ("2024-06-15T15:30:00", "20240615153000 +0000")
        ]
        
        for input_dt, expected in test_cases:
            result = _format_epg_datetime(input_dt)
            assert result == expected

    def test_invalid_datetime_string(self):
        """Test with invalid datetime string."""
        with pytest.raises(ValueError):
            _format_epg_datetime("invalid-datetime")

    def test_empty_string(self):
        """Test with empty string."""
        with pytest.raises(ValueError):
            _format_epg_datetime("")

    def test_none_input(self):
        """Test with None input."""
        with pytest.raises(TypeError):
            _format_epg_datetime(None)


class TestDatetimeToTimestamp:
    """Test suite for _datetime_to_timestamp function."""

    def test_valid_datetime_string(self):
        """Test converting valid datetime string to timestamp."""
        result = _datetime_to_timestamp("2024-01-01T12:30:45")
        # Should return integer timestamp
        assert isinstance(result, int)
        assert result > 0

    def test_invalid_datetime_string(self):
        """Test with invalid datetime string."""
        with pytest.raises(ValueError):
            _datetime_to_timestamp("invalid-datetime")

    def test_empty_string(self):
        """Test with empty string."""
        with pytest.raises(ValueError):
            _datetime_to_timestamp("")

    def test_none_input(self):
        """Test with None input."""
        with pytest.raises(TypeError):
            _datetime_to_timestamp(None)

    def test_malformed_datetime_string(self):
        """Test with malformed datetime string."""
        with pytest.raises(ValueError):
            _datetime_to_timestamp("2024-13-01T25:70:70")
