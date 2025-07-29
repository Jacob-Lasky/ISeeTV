"""Tests for ensure_file_exists function following atomic design principles."""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from common.file_utils import ensure_file_exists


class TestEnsureFileExists:
    """Test suite for ensure_file_exists function."""

    def test_ensure_file_exists_creates_empty_file_when_not_exists(self, tmp_path):
        """Test that empty file is created when file doesn't exist and no default content."""
        file_path = tmp_path / "new_file.txt"

        ensure_file_exists(str(file_path))

        assert file_path.exists()
        assert file_path.stat().st_size == 0

    def test_ensure_file_exists_does_not_modify_existing_file(self, tmp_path):
        """Test that existing files are not modified."""
        file_path = tmp_path / "existing.txt"
        original_content = "original content"
        file_path.write_text(original_content)
        original_mtime = file_path.stat().st_mtime

        ensure_file_exists(str(file_path))

        assert file_path.read_text() == original_content
        assert file_path.stat().st_mtime == original_mtime

    @pytest.mark.parametrize(
        "default_content",
        [
            {"key": "value"},
            [],
            {},
            {"nested": {"data": "value"}},
            {"list": [1, 2, 3]},
            {"unicode": "café"},
            {"complex": {"users": [{"id": 1, "name": "John"}]}},
        ],
    )
    def test_ensure_file_exists_creates_file_with_json_content(
        self, tmp_path, default_content
    ):
        """Test creating file with various JSON default content."""
        file_path = tmp_path / "with_content.json"

        ensure_file_exists(str(file_path), default_content)

        assert file_path.exists()
        content = json.loads(file_path.read_text())
        assert content == default_content

    def test_ensure_file_exists_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created when using JSON content."""
        nested_path = tmp_path / "nested" / "deep" / "file.json"
        default_content = {"test": "data"}

        ensure_file_exists(str(nested_path), default_content)

        assert nested_path.exists()
        assert nested_path.parent.exists()
        content = json.loads(nested_path.read_text())
        assert content == default_content
