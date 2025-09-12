"""Tests for LoadResult class following atomic design principles."""

import pytest
from ingest.epg_loader import LoadResult


class TestLoadResult:
    """Test LoadResult class functionality."""

    def test_load_result_initialization(self):
        """Test LoadResult initialization with all parameters."""
        result = LoadResult("EPG_CHANNEL", "test:channel1", "upserted", "Test message")
        
        assert result.record_type == "EPG_CHANNEL"
        assert result.record_id == "test:channel1"
        assert result.status == "upserted"
        assert result.message == "Test message"

    def test_load_result_initialization_without_message(self):
        """Test LoadResult initialization with default empty message."""
        result = LoadResult("PROGRAM", "test:prog1", "inserted")
        
        assert result.record_type == "PROGRAM"
        assert result.record_id == "test:prog1"
        assert result.status == "inserted"
        assert result.message == ""

    @pytest.mark.parametrize("record_type,record_id,status,message,expected", [
        ("EPG_CHANNEL", "test:channel1", "upserted", "Success", "EPG_CHANNEL[test:channel1]: upserted - Success"),
        ("PROGRAM", "test:prog1", "error", "Failed", "PROGRAM[test:prog1]: error - Failed"),
        ("EPG_CHANNEL", "test:channel2", "skipped", "", "EPG_CHANNEL[test:channel2]: skipped - "),
    ])
    def test_load_result_string_representation(self, record_type, record_id, status, message, expected):
        """Test LoadResult string representation."""
        result = LoadResult(record_type, record_id, status, message)
        assert str(result) == expected

    def test_load_result_with_unicode_characters(self):
        """Test LoadResult with unicode characters."""
        result = LoadResult("EPG_CHANNEL", "test:chännél", "upserted", "Tëst mëssägë")
        
        assert result.record_type == "EPG_CHANNEL"
        assert result.record_id == "test:chännél"
        assert result.status == "upserted"
        assert result.message == "Tëst mëssägë"
        assert "chännél" in str(result)
        assert "Tëst mëssägë" in str(result)

    def test_load_result_with_long_strings(self):
        """Test LoadResult with very long strings."""
        long_message = "A" * 1000
        result = LoadResult("EPG_CHANNEL", "test:channel1", "upserted", long_message)
        
        assert result.message == long_message
        assert len(str(result)) > 1000
