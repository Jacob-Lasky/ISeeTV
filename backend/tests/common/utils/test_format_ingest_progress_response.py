"""
Tests for format_ingest_progress_response function from common.utils.

Following atomic design principles:
- Single responsibility: Tests only format_ingest_progress_response function
- Pure functions: Each test validates one specific behavior
- No side effects: Tests are isolated and independent
"""

import pytest
from unittest.mock import patch

from common.utils import format_ingest_progress_response


class TestFormatIngestProgressResponse:
    """Test class for format_ingest_progress_response function."""

    def test_format_ingest_progress_response_single_task(self):
        """Test formatting single ingest progress task."""
        progress_data = {
            "ingest_m3u_test_20240127_143022": {
                "task_id": "ingest_m3u_test_20240127_143022",
                "status": "completed",
                "progress": 100,
                "current_item": "final_channel",
                "source_name": "test",
                "file_type": "m3u"
            }
        }
        
        result = format_ingest_progress_response(progress_data)
        
        expected = {"ingest": progress_data}
        assert result == expected
        assert "ingest" in result
        assert result["ingest"] == progress_data

    def test_format_ingest_progress_response_multiple_tasks(self):
        """Test formatting multiple ingest progress tasks."""
        progress_data = {
            "ingest_m3u_source1_20240127_143022": {
                "task_id": "ingest_m3u_source1_20240127_143022",
                "status": "completed",
                "progress": 100,
                "current_item": "channel_150"
            },
            "ingest_epg_source2_20240127_143023": {
                "task_id": "ingest_epg_source2_20240127_143023",
                "status": "running",
                "progress": 75,
                "current_item": "program_7500",
                "current_phase": "programs"
            },
            "ingest_m3u_source3_20240127_143024": {
                "task_id": "ingest_m3u_source3_20240127_143024",
                "status": "failed",
                "progress": 25,
                "error": "Parse error at line 150"
            }
        }
        
        result = format_ingest_progress_response(progress_data)
        
        expected = {"ingest": progress_data}
        assert result == expected
        assert "ingest" in result
        assert result["ingest"] == progress_data
        assert len(result["ingest"]) == 3

    def test_format_ingest_progress_response_empty_data(self):
        """Test formatting empty progress data."""
        progress_data = {}
        
        result = format_ingest_progress_response(progress_data)
        
        expected = {"ingest": {}}
        assert result == expected
        assert "ingest" in result
        assert result["ingest"] == {}

    def test_format_ingest_progress_response_complex_task_data(self):
        """Test formatting with complex ingest task data structures."""
        progress_data = {
            "ingest_epg_complex_20240127_143022": {
                "task_id": "ingest_epg_complex_20240127_143022",
                "status": "running",
                "progress": 85,
                "current_item": "program_8500",
                "current_phase": "programs",
                "source_name": "complex_source",
                "file_type": "epg",
                "started_at": "2024-01-27T14:30:22",
                "updated_at": "2024-01-27T14:35:15",
                "steps": {
                    "channels": {
                        "completed": True,
                        "count": 200,
                        "processed": 200,
                        "duration": 45.2
                    },
                    "programs": {
                        "completed": False,
                        "count": 10000,
                        "processed": 8500,
                        "duration": 180.8
                    }
                },
                "metadata": {
                    "file_size": 20971520,
                    "estimated_completion": "2024-01-27T14:45:30",
                    "items_per_second": 47.2
                }
            }
        }
        
        result = format_ingest_progress_response(progress_data)
        
        expected = {"ingest": progress_data}
        assert result == expected
        assert "ingest" in result
        
        # Verify complex nested data is preserved
        task_data = result["ingest"]["ingest_epg_complex_20240127_143022"]
        assert task_data["steps"]["channels"]["completed"] is True
        assert task_data["steps"]["programs"]["processed"] == 8500
        assert task_data["metadata"]["items_per_second"] == 47.2

    def test_format_ingest_progress_response_logger_called(self):
        """Test that logger.debug is called with correct parameters."""
        progress_data = {
            "test_task": {
                "task_id": "test_task",
                "status": "completed"
            }
        }
        
        with patch("common.utils.logger") as mock_logger:
            format_ingest_progress_response(progress_data)
            
            mock_logger.debug.assert_called_once_with(
                "Formatting ingest progress response for %s", progress_data
            )

    def test_format_ingest_progress_response_legacy_format_structure(self):
        """Test that the function returns the expected legacy format structure."""
        progress_data = {
            "task1": {"status": "running"},
            "task2": {"status": "completed"}
        }
        
        result = format_ingest_progress_response(progress_data)
        
        # Verify it's the expected legacy format with "ingest" wrapper
        assert isinstance(result, dict)
        assert len(result) == 1
        assert "ingest" in result
        assert result["ingest"] is progress_data

    @pytest.mark.parametrize(
        "progress_data",
        [
            # None input
            None,
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
                    "current_item": "final_item"
                }
            },
            # Multiple tasks with varying data
            {
                "task3": {"status": "running", "progress": 50, "current_phase": "channels"},
                "task4": {"status": "failed", "error": "Database error"},
                "task5": {"status": "completed", "progress": 100}
            },
            # Complex nested structures
            {
                "complex_task": {
                    "status": "running",
                    "nested": {
                        "level1": {
                            "level2": ["item1", "item2", "item3"]
                        }
                    }
                }
            }
        ],
    )
    def test_format_ingest_progress_response_various_inputs(self, progress_data):
        """Test formatting with various input data structures."""
        result = format_ingest_progress_response(progress_data)
        
        expected = {"ingest": progress_data}
        assert result == expected
        assert "ingest" in result
        assert result["ingest"] is progress_data

    def test_format_ingest_progress_response_preserves_data_references(self):
        """Test that the function preserves original data references."""
        original_data = {
            "task1": {"status": "running", "data": [1, 2, 3]}
        }
        
        result = format_ingest_progress_response(original_data)
        
        # Verify the original data reference is preserved
        assert result["ingest"] is original_data
        assert result["ingest"]["task1"]["data"] is original_data["task1"]["data"]

    def test_format_ingest_progress_response_immutable_wrapper(self):
        """Test that the function creates a new wrapper dict without modifying input."""
        progress_data = {
            "task1": {"status": "completed"}
        }
        original_keys = set(progress_data.keys())
        
        result = format_ingest_progress_response(progress_data)
        
        # Verify original data is unchanged
        assert set(progress_data.keys()) == original_keys
        assert "ingest" not in progress_data
        
        # Verify result has the wrapper
        assert "ingest" in result
        assert result["ingest"] == progress_data

    def test_format_ingest_progress_response_return_type(self):
        """Test that return type is always a dictionary with 'ingest' key."""
        test_cases = [
            {},
            {"single_task": {"status": "completed"}},
            {"task1": {"status": "running"}, "task2": {"status": "failed"}},
            None
        ]
        
        for test_data in test_cases:
            result = format_ingest_progress_response(test_data)
            
            assert isinstance(result, dict)
            assert len(result) == 1
            assert "ingest" in result
            assert result["ingest"] == test_data
