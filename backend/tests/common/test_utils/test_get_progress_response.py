"""
Tests for get_progress_response function from common.utils.

Following atomic design principles:
- Single responsibility: Tests only get_progress_response function
- Pure functions: Each test validates one specific behavior
- No side effects: Tests are isolated and independent
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, status

from common.utils import get_progress_response


class TestGetProgressResponse:
    """Test class for get_progress_response function."""

    @pytest.mark.parametrize(
        "task_type,task_id,progress_data,expected_result",
        [
            (
                "download",
                "download_m3u_test_20240127_143022",
                {
                    "download_m3u_test_20240127_143022": {
                        "status": "completed",
                        "progress": 100,
                        "file_size": 1024
                    }
                },
                {
                    "status": "completed",
                    "progress": 100,
                    "file_size": 1024
                }
            ),
            (
                "ingest",
                "ingest_epg_source_20240127_143022",
                {
                    "ingest_epg_source_20240127_143022": {
                        "status": "running",
                        "progress": 50,
                        "current_item": "channel_123"
                    }
                },
                {
                    "status": "running",
                    "progress": 50,
                    "current_item": "channel_123"
                }
            ),
        ],
    )
    def test_get_progress_response_success(self, task_type, task_id, progress_data, expected_result):
        """Test successful progress retrieval for existing tasks."""
        with patch("common.utils.get_progress") as mock_get_progress:
            mock_get_progress.return_value = progress_data
            
            result = get_progress_response(task_id, task_type)
            
            assert result == expected_result
            mock_get_progress.assert_called_once_with(task_type)

    @pytest.mark.parametrize(
        "task_type,task_id",
        [
            ("download", "nonexistent_download_task"),
            ("ingest", "nonexistent_ingest_task"),
            ("download", ""),
            ("ingest", "invalid_task_id_format"),
        ],
    )
    def test_get_progress_response_task_not_found(self, task_type, task_id):
        """Test HTTPException raised when task ID is not found."""
        with patch("common.utils.get_progress") as mock_get_progress:
            mock_get_progress.return_value = {}  # Empty progress data
            
            with pytest.raises(HTTPException) as exc_info:
                get_progress_response(task_id, task_type)
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert f"{task_type.title()} task {task_id} not found" in str(exc_info.value.detail)
            mock_get_progress.assert_called_once_with(task_type)

    def test_get_progress_response_partial_match(self):
        """Test that partial task ID matches don't return results."""
        progress_data = {
            "download_m3u_test_20240127_143022": {"status": "completed"},
            "download_m3u_other_20240127_143023": {"status": "running"},
        }
        
        with patch("common.utils.get_progress") as mock_get_progress:
            mock_get_progress.return_value = progress_data
            
            # Should not match partial task ID
            with pytest.raises(HTTPException) as exc_info:
                get_progress_response("download_m3u_test", "download")
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    def test_get_progress_response_case_sensitivity(self):
        """Test that task ID matching is case-sensitive."""
        progress_data = {
            "download_m3u_Test_20240127_143022": {"status": "completed"}
        }
        
        with patch("common.utils.get_progress") as mock_get_progress:
            mock_get_progress.return_value = progress_data
            
            # Should not match different case
            with pytest.raises(HTTPException) as exc_info:
                get_progress_response("download_m3u_test_20240127_143022", "download")
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    def test_get_progress_response_with_complex_data(self):
        """Test with complex nested progress data."""
        complex_progress = {
            "ingest_epg_complex_20240127_143022": {
                "status": "running",
                "progress": 75,
                "current_item": "program_456",
                "current_phase": "programs",
                "steps": {
                    "channels": {"completed": True, "count": 100},
                    "programs": {"completed": False, "count": 750, "processed": 500}
                },
                "metadata": {
                    "source_name": "complex",
                    "file_type": "epg",
                    "started_at": "2024-01-27T14:30:22"
                }
            }
        }
        
        with patch("common.utils.get_progress") as mock_get_progress:
            mock_get_progress.return_value = complex_progress
            
            result = get_progress_response("ingest_epg_complex_20240127_143022", "ingest")
            
            assert result == complex_progress["ingest_epg_complex_20240127_143022"]
            assert result["steps"]["channels"]["completed"] is True
            assert result["metadata"]["source_name"] == "complex"

    def test_get_progress_response_logger_called(self):
        """Test that logger.debug is called with correct parameters."""
        progress_data = {
            "test_task_id": {"status": "completed"}
        }
        
        with patch("common.utils.get_progress") as mock_get_progress, \
             patch("common.utils.logger") as mock_logger:
            mock_get_progress.return_value = progress_data
            
            get_progress_response("test_task_id", "download")
            
            mock_logger.debug.assert_called_once_with("Getting progress for %s", "test_task_id")

    def test_get_progress_response_get_progress_exception(self):
        """Test behavior when get_progress raises an exception."""
        with patch("common.utils.get_progress") as mock_get_progress:
            mock_get_progress.side_effect = Exception("Database error")
            
            with pytest.raises(Exception) as exc_info:
                get_progress_response("test_task_id", "download")
            
            assert str(exc_info.value) == "Database error"

    @pytest.mark.parametrize(
        "task_type",
        ["download", "ingest"],
    )
    def test_get_progress_response_empty_progress_data(self, task_type):
        """Test behavior with empty progress data for different task types."""
        with patch("common.utils.get_progress") as mock_get_progress:
            mock_get_progress.return_value = {}
            
            with pytest.raises(HTTPException) as exc_info:
                get_progress_response("any_task_id", task_type)
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert f"{task_type.title()} task any_task_id not found" in str(exc_info.value.detail)
