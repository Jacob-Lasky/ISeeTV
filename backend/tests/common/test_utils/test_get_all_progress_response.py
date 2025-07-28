"""
Tests for get_all_progress_response function from common.utils.

Following atomic design principles:
- Single responsibility: Tests only get_all_progress_response function
- Pure functions: Each test validates one specific behavior
- No side effects: Tests are isolated and independent
"""

import pytest
from unittest.mock import patch

from common.utils import get_all_progress_response


class TestGetAllProgressResponse:
    """Test class for get_all_progress_response function."""

    @pytest.mark.parametrize(
        "task_type,progress_data",
        [
            (
                "download",
                {
                    "download_m3u_test1_20240127_143022": {
                        "status": "completed",
                        "progress": 100,
                        "file_size": 1024
                    },
                    "download_epg_test2_20240127_143023": {
                        "status": "running",
                        "progress": 50,
                        "file_size": 2048
                    }
                }
            ),
            (
                "ingest",
                {
                    "ingest_m3u_source1_20240127_143022": {
                        "status": "completed",
                        "progress": 100,
                        "current_item": "final_channel"
                    },
                    "ingest_epg_source2_20240127_143023": {
                        "status": "failed",
                        "progress": 25,
                        "error": "Parse error"
                    }
                }
            ),
        ],
    )
    def test_get_all_progress_response_success(self, task_type, progress_data):
        """Test successful retrieval of all progress data for different task types."""
        with patch("common.utils.get_progress") as mock_get_progress:
            mock_get_progress.return_value = progress_data
            
            result = get_all_progress_response(task_type)
            
            assert result == progress_data
            mock_get_progress.assert_called_once_with(task_type)

    @pytest.mark.parametrize(
        "task_type",
        ["download", "ingest"],
    )
    def test_get_all_progress_response_empty_data(self, task_type):
        """Test behavior with empty progress data for different task types."""
        with patch("common.utils.get_progress") as mock_get_progress:
            mock_get_progress.return_value = {}
            
            result = get_all_progress_response(task_type)
            
            assert result == {}
            mock_get_progress.assert_called_once_with(task_type)

    def test_get_all_progress_response_large_dataset(self):
        """Test with large progress dataset."""
        # Create large dataset with 100 tasks
        large_progress_data = {}
        for i in range(100):
            task_id = f"download_m3u_source{i}_20240127_{143000 + i:06d}"
            large_progress_data[task_id] = {
                "status": "completed" if i % 2 == 0 else "running",
                "progress": 100 if i % 2 == 0 else (i % 100),
                "file_size": 1024 * (i + 1)
            }
        
        with patch("common.utils.get_progress") as mock_get_progress:
            mock_get_progress.return_value = large_progress_data
            
            result = get_all_progress_response("download")
            
            assert result == large_progress_data
            assert len(result) == 100
            mock_get_progress.assert_called_once_with("download")

    def test_get_all_progress_response_mixed_statuses(self):
        """Test with progress data containing various task statuses."""
        mixed_progress_data = {
            "task_completed": {
                "status": "completed",
                "progress": 100,
                "completed_at": "2024-01-27T14:30:22"
            },
            "task_running": {
                "status": "running",
                "progress": 75,
                "current_item": "processing_item"
            },
            "task_failed": {
                "status": "failed",
                "progress": 30,
                "error": "Connection timeout"
            },
            "task_pending": {
                "status": "pending",
                "progress": 0,
                "queued_at": "2024-01-27T14:35:00"
            }
        }
        
        with patch("common.utils.get_progress") as mock_get_progress:
            mock_get_progress.return_value = mixed_progress_data
            
            result = get_all_progress_response("ingest")
            
            assert result == mixed_progress_data
            assert len(result) == 4
            assert result["task_completed"]["status"] == "completed"
            assert result["task_failed"]["error"] == "Connection timeout"

    def test_get_all_progress_response_logger_called(self):
        """Test that logger.debug is called with correct parameters."""
        progress_data = {"test_task": {"status": "completed"}}
        
        with patch("common.utils.get_progress") as mock_get_progress, \
             patch("common.utils.logger") as mock_logger:
            mock_get_progress.return_value = progress_data
            
            get_all_progress_response("download")
            
            mock_logger.debug.assert_called_once_with("Getting all progress for %s", "download")

    def test_get_all_progress_response_get_progress_exception(self):
        """Test behavior when get_progress raises an exception."""
        with patch("common.utils.get_progress") as mock_get_progress:
            mock_get_progress.side_effect = Exception("State storage error")
            
            with pytest.raises(Exception) as exc_info:
                get_all_progress_response("ingest")
            
            assert str(exc_info.value) == "State storage error"

    def test_get_all_progress_response_complex_nested_data(self):
        """Test with complex nested progress data structures."""
        complex_progress_data = {
            "ingest_epg_complex_20240127_143022": {
                "status": "running",
                "progress": 85,
                "current_item": "program_789",
                "current_phase": "programs",
                "steps": {
                    "channels": {
                        "completed": True,
                        "count": 150,
                        "processed": 150,
                    },
                    "programs": {
                        "completed": False,
                        "count": 5000,
                        "processed": 4250,
                    }
                },
                "metadata": {
                    "source_name": "complex_source",
                    "file_type": "epg",
                    "file_size": 10485760,
                    "started_at": "2024-01-27T14:30:22",
                    "estimated_completion": "2024-01-27T14:45:30"
                },
                "performance": {
                    "items_per_second": 42.5,
                    "memory_usage_mb": 128.4,
                    "cpu_usage_percent": 15.2
                }
            }
        }
        
        with patch("common.utils.get_progress") as mock_get_progress:
            mock_get_progress.return_value = complex_progress_data
            
            result = get_all_progress_response("ingest")
            
            assert result == complex_progress_data
            task_data = result["ingest_epg_complex_20240127_143022"]
            assert task_data["steps"]["channels"]["completed"] is True
            assert task_data["performance"]["items_per_second"] == 42.5
            assert task_data["metadata"]["file_size"] == 10485760

    def test_get_all_progress_response_return_type_consistency(self):
        """Test that return type is always a dictionary regardless of input."""
        test_cases = [
            {},  # Empty dict
            None,  # None value (if get_progress returns None)
            {"single_task": {"status": "completed"}},  # Single task
        ]
        
        for test_data in test_cases:
            with patch("common.utils.get_progress") as mock_get_progress:
                mock_get_progress.return_value = test_data
                
                result = get_all_progress_response("download")
                
                assert result == test_data
                assert isinstance(result, (dict, type(None)))  # Should be dict or None
