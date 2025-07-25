"""Tests for LoadResult class in M3U loader."""

import pytest

from ingest.m3u_loader import LoadResult


class TestLoadResult:
    """Test cases for LoadResult class."""

    def test_load_result_creation(self):
        """Test LoadResult creation with all parameters."""
        result = LoadResult("M3U_CHANNEL", "test_id", "inserted", "Test message")
        
        assert result.record_type == "M3U_CHANNEL"
        assert result.record_id == "test_id"
        assert result.status == "inserted"
        assert result.message == "Test message"

    def test_load_result_creation_without_message(self):
        """Test LoadResult creation without message parameter."""
        result = LoadResult("M3U_CHANNEL", "test_id", "updated")
        
        assert result.record_type == "M3U_CHANNEL"
        assert result.record_id == "test_id"
        assert result.status == "updated"
        assert result.message == ""

    @pytest.mark.parametrize("record_type,record_id,status,message,expected", [
        ("M3U_CHANNEL", "ch1", "inserted", "Success", "M3U_CHANNEL[ch1]: inserted - Success"),
        ("M3U_CHANNEL", "ch2", "updated", "", "M3U_CHANNEL[ch2]: updated - "),
        ("M3U_CHANNEL", "ch3", "error", "Database error", "M3U_CHANNEL[ch3]: error - Database error"),
        ("M3U_CHANNEL", "ch4", "skipped", "Already exists", "M3U_CHANNEL[ch4]: skipped - Already exists"),
    ])
    def test_load_result_string_representation(self, record_type, record_id, status, message, expected):
        """Test LoadResult string representation for various scenarios."""
        result = LoadResult(record_type, record_id, status, message)
        assert str(result) == expected

    def test_load_result_with_unicode_characters(self):
        """Test LoadResult with unicode characters in fields."""
        result = LoadResult("M3U_CHANNEL", "测试频道", "inserted", "成功插入频道")
        
        assert result.record_type == "M3U_CHANNEL"
        assert result.record_id == "测试频道"
        assert result.status == "inserted"
        assert result.message == "成功插入频道"
        assert str(result) == "M3U_CHANNEL[测试频道]: inserted - 成功插入频道"

    def test_load_result_with_long_strings(self):
        """Test LoadResult with very long strings."""
        long_id = "a" * 1000
        long_message = "b" * 2000
        
        result = LoadResult("M3U_CHANNEL", long_id, "inserted", long_message)
        
        assert result.record_id == long_id
        assert result.message == long_message
        assert len(str(result)) > 3000

    def test_load_result_with_special_characters(self):
        """Test LoadResult with special characters and symbols."""
        result = LoadResult(
            "M3U_CHANNEL", 
            "ch:1@test.com", 
            "inserted", 
            "Channel with special chars: !@#$%^&*()"
        )
        
        assert result.record_id == "ch:1@test.com"
        assert result.message == "Channel with special chars: !@#$%^&*()"
        assert "ch:1@test.com" in str(result)
