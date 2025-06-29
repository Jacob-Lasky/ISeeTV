"""
This module provides a centralized location for global state that needs to be
accessed across multiple modules.
"""

from typing import Dict, Literal
import logging

logger = logging.getLogger(__name__)

# Global state for tracking download progress
# This is the single source of truth for all download progress data
download_progress: Dict[str, Dict] = {}
ingest_progress: Dict[str, Dict] = {}

# Global state for tracking cancelled downloads
# Tasks in this set should be cancelled
cancelled_tasks: set = set()


def get_progress(task_type: Literal["download", "ingest"]) -> Dict[str, Dict]:
    """Get the global download progress dictionary"""
    if task_type == "download":
        return download_progress
    elif task_type == "ingest":
        return ingest_progress


def clear_progress(task_type: Literal["download", "ingest"]) -> None:
    """Clear all download progress (useful for testing)"""
    if task_type == "download":
        global download_progress
        download_progress.clear()
    elif task_type == "ingest":
        global ingest_progress
        ingest_progress.clear()


def cancel_task(task_id: str, task_type: Literal["download", "ingest"]) -> bool:
    """Cancel a download task by adding it to the cancelled tasks set"""
    global cancelled_tasks

    # Check if task exists in progress
    if task_id in get_progress(task_type):
        cancelled_tasks.add(task_id)

        # Update the task status to 'failed' with cancellation message
        if task_id in get_progress(task_type):
            get_progress(task_type)[task_id]["status"] = "failed"
            get_progress(task_type)[task_id][
                "error_message"
            ] = f"{task_type.title()} task cancelled by user"

        logger.info(f"{task_type.title()} task {task_id} marked for cancellation")
        return True

    return False


def is_task_cancelled(task_id: str) -> bool:
    """Check if a task has been cancelled"""
    return task_id in cancelled_tasks


def remove_cancelled_task(task_id: str) -> None:
    """Remove a task from the cancelled tasks set (cleanup)"""
    global cancelled_tasks
    cancelled_tasks.discard(task_id)
