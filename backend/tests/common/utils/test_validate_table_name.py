"""
Tests for validate_table_name function from common.utils.

Following atomic design principles:
- Single responsibility: Tests only validate_table_name function
- Pure functions: Each test validates one specific behavior
- No side effects: Tests are isolated and independent
"""

import pytest
from unittest.mock import patch
from fastapi import HTTPException, status

from common.utils import validate_table_name


class TestValidateTableName:
    """Test class for validate_table_name function."""

    @pytest.fixture
    def mock_filterable_columns_config(self):
        """Mock FILTERABLE_COLUMNS_CONFIG for testing."""
        return {
            "m3u_channels": ["id", "name", "source"],
            "epg_channels": ["id", "display_name", "source"],
            "programs": ["id", "title", "channel_id"],
            "streams": ["id", "name", "url"]
        }

    def test_validate_table_name_valid_tables_with_streams(self, mock_filterable_columns_config):
        """Test validation with valid table names when streams is included."""
        with patch("common.utils.FILTERABLE_COLUMNS_CONFIG", mock_filterable_columns_config):
            # Should not raise exception for valid tables
            validate_table_name("m3u_channels", include_streams=True)
            validate_table_name("epg_channels", include_streams=True)
            validate_table_name("programs", include_streams=True)
            validate_table_name("streams", include_streams=True)

    def test_validate_table_name_valid_tables_without_streams(self, mock_filterable_columns_config):
        """Test validation with valid table names when streams is excluded."""
        with patch("common.utils.FILTERABLE_COLUMNS_CONFIG", mock_filterable_columns_config):
            # Should not raise exception for valid non-streams tables
            validate_table_name("m3u_channels", include_streams=False)
            validate_table_name("epg_channels", include_streams=False)
            validate_table_name("programs", include_streams=False)

    def test_validate_table_name_streams_excluded(self, mock_filterable_columns_config):
        """Test that streams table is rejected when include_streams=False."""
        with patch("common.utils.FILTERABLE_COLUMNS_CONFIG", mock_filterable_columns_config):
            with pytest.raises(HTTPException) as exc_info:
                validate_table_name("streams", include_streams=False)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            expected_valid_tables = ["m3u_channels", "epg_channels", "programs"]
            assert f"Invalid table name. Must be one of: {expected_valid_tables}" in str(exc_info.value.detail)

    @pytest.mark.parametrize(
        "invalid_table_name",
        [
            "invalid_table",
            "users",
            "admin",
            "system",
            "",
            "m3u_channels; DROP TABLE users;",
            "m3u_channels--",
            "' OR 1=1 --",
            "SELECT * FROM users",
            "../../etc/passwd",
            "null",
            "undefined",
            123,  # This would be caught by type checker, but testing runtime behavior
        ],
    )
    def test_validate_table_name_invalid_tables(self, invalid_table_name, mock_filterable_columns_config):
        """Test validation with various invalid table names."""
        with patch("common.utils.FILTERABLE_COLUMNS_CONFIG", mock_filterable_columns_config):
            with pytest.raises(HTTPException) as exc_info:
                validate_table_name(str(invalid_table_name), include_streams=True)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid table name" in str(exc_info.value.detail)

    def test_validate_table_name_case_sensitivity(self, mock_filterable_columns_config):
        """Test that table name validation is case-sensitive."""
        with patch("common.utils.FILTERABLE_COLUMNS_CONFIG", mock_filterable_columns_config):
            # Should raise exception for different case
            with pytest.raises(HTTPException) as exc_info:
                validate_table_name("M3U_CHANNELS", include_streams=True)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            
            with pytest.raises(HTTPException) as exc_info:
                validate_table_name("Streams", include_streams=True)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_table_name_default_include_streams(self, mock_filterable_columns_config):
        """Test that include_streams defaults to True."""
        with patch("common.utils.FILTERABLE_COLUMNS_CONFIG", mock_filterable_columns_config):
            # Should not raise exception when called without include_streams parameter
            validate_table_name("streams")  # Default should include streams
            validate_table_name("m3u_channels")  # Other tables should also work

    def test_validate_table_name_empty_config(self):
        """Test behavior with empty FILTERABLE_COLUMNS_CONFIG."""
        with patch("common.utils.FILTERABLE_COLUMNS_CONFIG", {}):
            with pytest.raises(HTTPException) as exc_info:
                validate_table_name("any_table", include_streams=True)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid table name. Must be one of: []" in str(exc_info.value.detail)

    def test_validate_table_name_config_without_streams(self):
        """Test behavior when FILTERABLE_COLUMNS_CONFIG doesn't contain streams."""
        config_without_streams = {
            "m3u_channels": ["id", "name"],
            "epg_channels": ["id", "display_name"],
            "programs": ["id", "title"]
        }
        
        with patch("common.utils.FILTERABLE_COLUMNS_CONFIG", config_without_streams):
            # Should work for existing tables
            validate_table_name("m3u_channels", include_streams=True)
            
            # Should fail for streams even with include_streams=True
            with pytest.raises(HTTPException) as exc_info:
                validate_table_name("streams", include_streams=True)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_table_name_sql_injection_attempts(self, mock_filterable_columns_config):
        """Test that common SQL injection attempts are blocked."""
        sql_injection_attempts = [
            "m3u_channels; DROP TABLE users;",
            "m3u_channels' OR '1'='1",
            "m3u_channels UNION SELECT * FROM users",
            "m3u_channels--",
            "m3u_channels/*comment*/",
            "m3u_channels\x00",  # Null byte injection
            "m3u_channels\r\nDROP TABLE users;",
            "../../../etc/passwd",
            "m3u_channels\"; DROP TABLE users; --"
        ]
        
        with patch("common.utils.FILTERABLE_COLUMNS_CONFIG", mock_filterable_columns_config):
            for injection_attempt in sql_injection_attempts:
                with pytest.raises(HTTPException) as exc_info:
                    validate_table_name(injection_attempt, include_streams=True)
                
                assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
                assert "Invalid table name" in str(exc_info.value.detail)

    def test_validate_table_name_whitespace_handling(self, mock_filterable_columns_config):
        """Test handling of whitespace in table names."""
        whitespace_variants = [
            " m3u_channels",
            "m3u_channels ",
            " m3u_channels ",
            "m3u_channels\t",
            "m3u_channels\n",
            "m3u channels",  # Space in middle
            "\tm3u_channels\n"
        ]
        
        with patch("common.utils.FILTERABLE_COLUMNS_CONFIG", mock_filterable_columns_config):
            for variant in whitespace_variants:
                with pytest.raises(HTTPException) as exc_info:
                    validate_table_name(variant, include_streams=True)
                
                assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_table_name_unicode_characters(self, mock_filterable_columns_config):
        """Test handling of unicode characters in table names."""
        unicode_variants = [
            "m3u_channels测试",
            "频道表",
            "m3u_channels🎬",
            "таблица",
            "テーブル"
        ]
        
        with patch("common.utils.FILTERABLE_COLUMNS_CONFIG", mock_filterable_columns_config):
            for variant in unicode_variants:
                with pytest.raises(HTTPException) as exc_info:
                    validate_table_name(variant, include_streams=True)
                
                assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_table_name_return_value(self, mock_filterable_columns_config):
        """Test that function returns None on successful validation."""
        with patch("common.utils.FILTERABLE_COLUMNS_CONFIG", mock_filterable_columns_config):
            result = validate_table_name("m3u_channels", include_streams=True)
            assert result is None

    def test_validate_table_name_error_message_format(self, mock_filterable_columns_config):
        """Test that error message contains correct format and valid tables list."""
        with patch("common.utils.FILTERABLE_COLUMNS_CONFIG", mock_filterable_columns_config):
            # Test with include_streams=True
            with pytest.raises(HTTPException) as exc_info:
                validate_table_name("invalid_table", include_streams=True)
            
            expected_tables = list(mock_filterable_columns_config.keys())
            assert f"Invalid table name. Must be one of: {expected_tables}" in str(exc_info.value.detail)
            
            # Test with include_streams=False
            with pytest.raises(HTTPException) as exc_info:
                validate_table_name("invalid_table", include_streams=False)
            
            expected_tables_no_streams = [t for t in mock_filterable_columns_config.keys() if t != "streams"]
            assert f"Invalid table name. Must be one of: {expected_tables_no_streams}" in str(exc_info.value.detail)
