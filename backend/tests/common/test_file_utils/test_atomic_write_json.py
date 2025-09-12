"""Tests for atomic_write_json function following atomic design principles."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from common.file_utils import atomic_write_json


class TestAtomicWriteJson:
    """Test suite for atomic_write_json function."""

    @pytest.mark.parametrize(
        "data,expected_content",
        [
            ({"key": "value"}, '{\n  "key": "value"\n}'),
            ([], "[]"),
            ({}, "{}"),
            (
                {"nested": {"key": "value"}},
                '{\n  "nested": {\n    "key": "value"\n  }\n}',
            ),
            ({"unicode": "café"}, '{\n  "unicode": "café"\n}'),
            ({"number": 42, "float": 3.14}, '{\n  "number": 42,\n  "float": 3.14\n}'),
            (
                {"boolean": True, "null": None},
                '{\n  "boolean": true,\n  "null": null\n}',
            ),
        ],
    )
    def test_atomic_write_json_success(self, tmp_path, data, expected_content):
        """Test successful JSON writing with various data types."""
        file_path = tmp_path / "test.json"

        atomic_write_json(str(file_path), data)

        assert file_path.exists()
        content = file_path.read_text(encoding="utf-8")
        assert content == expected_content

    def test_atomic_write_json_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created if they don't exist."""
        nested_path = tmp_path / "nested" / "deep" / "test.json"
        data = {"test": "data"}

        atomic_write_json(str(nested_path), data)

        assert nested_path.exists()
        assert nested_path.parent.exists()
        content = json.loads(nested_path.read_text())
        assert content == data

    def test_atomic_write_json_overwrites_existing_file(self, tmp_path):
        """Test that existing files are properly overwritten."""
        file_path = tmp_path / "existing.json"
        file_path.write_text("old content")

        new_data = {"new": "content"}
        atomic_write_json(str(file_path), new_data)

        content = json.loads(file_path.read_text())
        assert content == new_data

    def test_atomic_write_json_unicode_handling(self, tmp_path):
        """Test proper Unicode handling."""
        file_path = tmp_path / "unicode.json"
        unicode_data = {
            "english": "hello",
            "french": "café",
            "japanese": "こんにちは",
            "emoji": "🚀",
            "special": 'quotes"and\\backslashes',
        }

        atomic_write_json(str(file_path), unicode_data)

        content = json.loads(file_path.read_text(encoding="utf-8"))
        assert content == unicode_data

    def test_atomic_write_json_non_serializable_data_raises_error(self, tmp_path):
        """Test that non-serializable data raises JSONEncodeError."""
        file_path = tmp_path / "invalid.json"
        non_serializable_data = {"function": lambda x: x}

        with pytest.raises(
            TypeError
        ):  # json.JSONEncodeError is a subclass of TypeError
            atomic_write_json(str(file_path), non_serializable_data)

        # File should not exist after failed write
        assert not file_path.exists()

    @patch("tempfile.mkstemp")
    def test_atomic_write_json_temp_file_creation_error(self, mock_mkstemp, tmp_path):
        """Test handling of temporary file creation errors."""
        mock_mkstemp.side_effect = OSError("Cannot create temp file")
        file_path = tmp_path / "test.json"

        with pytest.raises(OSError, match="Cannot create temp file"):
            atomic_write_json(str(file_path), {"test": "data"})

    @patch("os.replace")
    def test_atomic_write_json_replace_error_cleans_temp_file(
        self, mock_replace, tmp_path
    ):
        """Test that temporary files are cleaned up when os.replace fails."""
        mock_replace.side_effect = OSError("Replace failed")
        file_path = tmp_path / "test.json"

        with pytest.raises(OSError, match="Replace failed"):
            atomic_write_json(str(file_path), {"test": "data"})

        # Verify no temporary files are left behind
        temp_files = list(tmp_path.glob(".*tmp"))
        assert len(temp_files) == 0

    @patch("os.fdopen")
    def test_atomic_write_json_write_error_cleans_temp_file(
        self, mock_fdopen, tmp_path
    ):
        """Test that temporary files are cleaned up when writing fails."""
        mock_file = Mock()
        mock_file.write.side_effect = OSError("Write failed")
        mock_fdopen.return_value.__enter__.return_value = mock_file

        file_path = tmp_path / "test.json"

        with pytest.raises(OSError, match="Write failed"):
            atomic_write_json(str(file_path), {"test": "data"})

        # Verify no temporary files are left behind
        temp_files = list(tmp_path.glob(".*tmp"))
        assert len(temp_files) == 0

    def test_atomic_write_json_preserves_file_atomicity(self, tmp_path):
        """Test that file operations are truly atomic (all-or-nothing)."""
        file_path = tmp_path / "atomic.json"
        original_data = {"original": "content"}

        # Create initial file
        atomic_write_json(str(file_path), original_data)

        # Simulate interruption during write by mocking os.replace to fail
        with patch("os.replace", side_effect=OSError("Simulated failure")):
            with pytest.raises(OSError):
                atomic_write_json(str(file_path), {"new": "content"})

        # Original file should still exist with original content
        assert file_path.exists()
        content = json.loads(file_path.read_text())
        assert content == original_data
