"""Atomic file operations utilities following atomic design principles.

This module provides atomic file operations that ensure data integrity
through temporary file writes and atomic moves.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from common.log_utils import get_logger

logger = get_logger(__name__)


def atomic_write_json(file_path: str, data: Any) -> None:
    """Atomically write JSON data to a file using temporary file and move.

    This ensures that the file is either completely written or not written at all,
    preventing corruption from partial writes.

    Args:
        file_path: Target file path to write to
        data: Data to serialize as JSON

    Raises:
        OSError: If file operations fail
        json.JSONEncodeError: If data cannot be serialized to JSON

    """
    logger.info("Atomically writing JSON to %s", file_path)

    # Ensure parent directory exists
    parent_dir = Path(file_path).parent
    parent_dir.mkdir(parents=True, exist_ok=True)

    # Write to temporary file first
    temp_fd, temp_path = tempfile.mkstemp(
        dir=parent_dir, prefix=f".{Path(file_path).name}.", suffix=".tmp"
    )

    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
            json.dump(data, temp_file, indent=2, ensure_ascii=False)
            temp_file.flush()
            os.fsync(temp_file.fileno())  # Ensure data is written to disk

        # Atomically move temporary file to target location
        os.replace(temp_path, file_path)
        logger.info("Successfully wrote JSON to %s", file_path)

    except Exception:
        # Clean up temporary file on error
        os.unlink(temp_path)
        raise


def atomic_read_json(file_path: str, default: Any = None) -> Any:
    """Atomically read JSON data from a file with fallback to default.

    Args:
        file_path: Path to JSON file to read
        default: Default value to return if file doesn't exist or is invalid

    Returns:
        Parsed JSON data or default value

    """
    logger.info("Reading JSON from %s", file_path)

    try:
        if not os.path.exists(file_path):
            logger.info("File %s does not exist, returning default", file_path)
            return default

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            logger.info("Successfully read JSON from %s", file_path)
            return data

    except (json.JSONDecodeError, OSError) as e:
        logger.warning(
            "Failed to read JSON from %s: %s, returning default", file_path, e
        )
        return default


def ensure_file_exists(file_path: str, default_content: Any = None) -> None:
    """Ensure a file exists, creating it with default content if it doesn't.

    Args:
        file_path: Path to file to ensure exists
        default_content: Default content to write if file doesn't exist

    """
    if not os.path.exists(file_path):
        logger.info("Creating file %s with default content", file_path)
        if default_content is not None:
            atomic_write_json(file_path, default_content)
        else:
            # Create empty file
            Path(file_path).touch()
