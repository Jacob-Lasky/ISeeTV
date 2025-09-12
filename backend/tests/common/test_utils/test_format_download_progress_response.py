"""
Tests for format_download_progress_response function from common.utils.

Following atomic design principles:
- Single responsibility: Tests only format_download_progress_response function
- Pure functions: Each test validates one specific behavior
- No side effects: Tests are isolated and independent
"""

import pytest
from unittest.mock import patch, MagicMock

from common.utils import format_download_progress_response


class TestFormatDownloadProgressResponse:
    """Test class for format_download_progress_response function."""

    def test_format_download_progress_response_single_task(self):
        """Test formatting single download progress task."""
        progress_data = {
            "download_m3u_test_20240127_143022": {
                "task_id": "download_m3u_test_20240127_143022",
                "status": "completed",
                "progress": 100,
                "file_size": 1024,
                "downloaded_bytes": 1024,
                "source_name": "test",
                "file_type": "m3u"
            }
        }
        
        with patch("common.utils.DownloadProgress") as mock_download_progress:
            mock_instance = MagicMock()
            mock_download_progress.return_value = mock_instance
            
            result = format_download_progress_response(progress_data)
            
            assert len(result) == 1
            assert "download_m3u_test_20240127_143022" in result
            assert result["download_m3u_test_20240127_143022"] == mock_instance
            mock_download_progress.assert_called_once_with(**progress_data["download_m3u_test_20240127_143022"])

    def test_format_download_progress_response_multiple_tasks(self):
        """Test formatting multiple download progress tasks."""
        progress_data = {
            "download_m3u_source1_20240127_143022": {
                "task_id": "download_m3u_source1_20240127_143022",
                "status": "completed",
                "progress": 100,
                "file_size": 1024
            },
            "download_epg_source2_20240127_143023": {
                "task_id": "download_epg_source2_20240127_143023",
                "status": "running",
                "progress": 75,
                "file_size": 2048
            },
            "download_m3u_source3_20240127_143024": {
                "task_id": "download_m3u_source3_20240127_143024",
                "status": "failed",
                "progress": 25,
                "error": "Connection timeout"
            }
        }
        
        with patch("common.utils.DownloadProgress") as mock_download_progress:
            mock_instances = [MagicMock(), MagicMock(), MagicMock()]
            mock_download_progress.side_effect = mock_instances
            
            result = format_download_progress_response(progress_data)
            
            assert len(result) == 3
            assert len(mock_download_progress.call_args_list) == 3
            
            # Verify each task is processed correctly
            for i, (task_id, task_data) in enumerate(progress_data.items()):
                assert task_id in result
                assert result[task_id] == mock_instances[i]
                assert mock_download_progress.call_args_list[i][1] == task_data

    def test_format_download_progress_response_empty_data(self):
        """Test formatting empty progress data."""
        progress_data = {}
        
        result = format_download_progress_response(progress_data)
        
        assert result == {}
        assert isinstance(result, dict)

    def test_format_download_progress_response_complex_task_data(self):
        """Test formatting with complex task data structures."""
        progress_data = {
            "download_epg_complex_20240127_143022": {
                "task_id": "download_epg_complex_20240127_143022",
                "status": "running",
                "progress": 65,
                "file_size": 10485760,
                "downloaded_bytes": 6815744,
                "source_name": "complex_source",
                "file_type": "epg",
                "url": "https://example.com/epg.xml",
                "started_at": "2024-01-27T14:30:22",
                "updated_at": "2024-01-27T14:32:15",
                "download_speed": 1048576,
                "eta_seconds": 3.5,
                "metadata": {
                    "content_type": "application/xml",
                    "last_modified": "2024-01-27T12:00:00",
                    "compression": "gzip"
                }
            }
        }
        
        with patch("common.utils.DownloadProgress") as mock_download_progress:
            mock_instance = MagicMock()
            mock_download_progress.return_value = mock_instance
            
            result = format_download_progress_response(progress_data)
            
            assert len(result) == 1
            task_id = "download_epg_complex_20240127_143022"
            assert task_id in result
            assert result[task_id] == mock_instance
            
            # Verify DownloadProgress was called with all the complex data
            call_args = mock_download_progress.call_args[1]
            assert call_args["file_size"] == 10485760
            assert call_args["metadata"]["compression"] == "gzip"

    def test_format_download_progress_response_download_progress_exception(self):
        """Test behavior when DownloadProgress constructor raises exception."""
        progress_data = {
            "invalid_task": {
                "invalid_field": "invalid_value"
            }
        }
        
        with patch("common.utils.DownloadProgress") as mock_download_progress:
            mock_download_progress.side_effect = ValueError("Invalid field")
            
            with pytest.raises(ValueError) as exc_info:
                format_download_progress_response(progress_data)
            
            assert str(exc_info.value) == "Invalid field"

    @pytest.mark.parametrize(
        "progress_data",
        [
            # Single task with minimal data
            {
                "task1": {"status": "pending"}
            },
            # Single task with full data
            {
                "task2": {
                    "task_id": "task2",
                    "status": "completed",
                    "progress": 100,
                    "file_size": 1024,
                    "downloaded_bytes": 1024
                }
            },
            # Multiple tasks with varying data
            {
                "task3": {"status": "running", "progress": 50},
                "task4": {"status": "failed", "error": "Network error"},
                "task5": {"status": "completed", "progress": 100}
            }
        ],
    )
    def test_format_download_progress_response_various_data_structures(self, progress_data):
        """Test formatting with various data structures."""
        with patch("common.utils.DownloadProgress") as mock_download_progress:
            mock_instances = [MagicMock() for _ in progress_data]
            mock_download_progress.side_effect = mock_instances
            
            result = format_download_progress_response(progress_data)
            
            assert len(result) == len(progress_data)
            assert len(mock_download_progress.call_args_list) == len(progress_data)
            
            for i, task_id in enumerate(progress_data.keys()):
                assert task_id in result
                assert result[task_id] == mock_instances[i]

    def test_format_download_progress_response_preserves_task_ids(self):
        """Test that task IDs are preserved as dictionary keys."""
        task_ids = [
            "download_m3u_test1_20240127_143022",
            "download_epg_test2_20240127_143023",
            "download_m3u_special-chars_20240127_143024",
            "download_epg_unicode_测试_20240127_143025"
        ]
        
        progress_data = {
            task_id: {"task_id": task_id, "status": "completed"}
            for task_id in task_ids
        }
        
        with patch("common.utils.DownloadProgress") as mock_download_progress:
            mock_download_progress.return_value = MagicMock()
            
            result = format_download_progress_response(progress_data)
            
            assert set(result.keys()) == set(task_ids)
            for task_id in task_ids:
                assert task_id in result
