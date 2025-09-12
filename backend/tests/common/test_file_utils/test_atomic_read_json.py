"""Tests for atomic_read_json function following atomic design principles."""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from common.file_utils import atomic_read_json


class TestAtomicReadJson:
    """Test suite for atomic_read_json function."""

    @pytest.mark.parametrize(
        "data,expected",
        [
            ({"key": "value"}, {"key": "value"}),
            ([], []),
            ({}, {}),
            ({"nested": {"key": "value"}}, {"nested": {"key": "value"}}),
            ({"unicode": "café"}, {"unicode": "café"}),
            ({"number": 42, "float": 3.14}, {"number": 42, "float": 3.14}),
            ({"boolean": True, "null": None}, {"boolean": True, "null": None}),
            ([1, 2, 3], [1, 2, 3]),
            ("simple string", "simple string"),
            (42, 42),
            (True, True),
            (None, None),
        ],
    )
    def test_atomic_read_json_success(self, tmp_path, data, expected):
        """Test successful JSON reading with various data types."""
        file_path = tmp_path / "test.json"

        # Write test data
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        result = atomic_read_json(str(file_path))

        assert result == expected

    @pytest.mark.parametrize(
        "default",
        [
            None,
            {},
            [],
            {"default": "value"},
            "default_string",
            42,
            False,
        ],
    )
    def test_atomic_read_json_file_not_exists_returns_default(self, tmp_path, default):
        """Test that default value is returned when file doesn't exist."""
        non_existent_path = tmp_path / "nonexistent.json"

        result = atomic_read_json(str(non_existent_path), default)

        assert result == default

    def test_atomic_read_json_file_not_exists_no_default(self, tmp_path):
        """Test that None is returned when file doesn't exist and no default provided."""
        non_existent_path = tmp_path / "nonexistent.json"

        result = atomic_read_json(str(non_existent_path))

        assert result is None

    @pytest.mark.parametrize(
        "invalid_content,default",
        [
            ("invalid json content", {}),
            ("{invalid: json}", []),
            ("{'single_quotes': 'not_valid_json'}", None),
            ("{", {"fallback": True}),
            ("", "empty_fallback"),
            ("null null", 42),
        ],
    )
    def test_atomic_read_json_invalid_json_returns_default(
        self, tmp_path, invalid_content, default
    ):
        """Test that default value is returned when JSON is invalid."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text(invalid_content, encoding="utf-8")

        result = atomic_read_json(str(file_path), default)

        assert result == default

    def test_atomic_read_json_unicode_handling(self, tmp_path):
        """Test proper Unicode handling."""
        file_path = tmp_path / "unicode.json"
        unicode_data = {
            "english": "hello",
            "french": "café",
            "japanese": "こんにちは",
            "emoji": "🚀",
            "special": 'quotes"and\\backslashes',
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(unicode_data, f, ensure_ascii=False)

        result = atomic_read_json(str(file_path))

        assert result == unicode_data

    @patch("builtins.open")
    def test_atomic_read_json_os_error_returns_default(self, mock_open, tmp_path):
        """Test that OSError during file reading returns default value."""
        mock_open.side_effect = OSError("Permission denied")
        file_path = tmp_path / "test.json"
        default_value = {"error": "fallback"}

        result = atomic_read_json(str(file_path), default_value)

        assert result == default_value

    def test_atomic_read_json_empty_file_returns_default(self, tmp_path):
        """Test that empty file returns default value."""
        file_path = tmp_path / "empty.json"
        file_path.touch()  # Create empty file
        default_value = {"empty": "fallback"}

        result = atomic_read_json(str(file_path), default_value)

        assert result == default_value

    def test_atomic_read_json_whitespace_only_file_returns_default(self, tmp_path):
        """Test that file with only whitespace returns default value."""
        file_path = tmp_path / "whitespace.json"
        file_path.write_text("   \n\t  \n  ", encoding="utf-8")
        default_value = {"whitespace": "fallback"}

        result = atomic_read_json(str(file_path), default_value)

        assert result == default_value

    @patch("os.path.exists")
    def test_atomic_read_json_exists_check_error_returns_default(
        self, mock_exists, tmp_path
    ):
        """Test that errors during file existence check return default value."""
        mock_exists.side_effect = OSError("Access denied")
        file_path = tmp_path / "test.json"
        default_value = {"access": "denied"}

        result = atomic_read_json(str(file_path), default_value)

        assert result == default_value

    def test_atomic_read_json_file_encoding_handling(self, tmp_path):
        """Test that files are properly read with UTF-8 encoding."""
        file_path = tmp_path / "encoding.json"

        # Write file with explicit UTF-8 encoding
        data = {"encoding": "test", "special": "café"}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        result = atomic_read_json(str(file_path))

        assert result == data
        assert result["special"] == "café"
