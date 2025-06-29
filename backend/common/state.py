"""
This module provides a centralized location for global state that needs to be
accessed across multiple modules.
"""

from typing import Dict
import logging

logger = logging.getLogger(__name__)

# Global state for tracking download progress
# This is the single source of truth for all download progress data
download_progress: Dict[str, Dict] = {}

# Global state for tracking cancelled downloads
# Tasks in this set should be cancelled
cancelled_tasks: set = set()


def get_download_progress() -> Dict[str, Dict]:
    """Get the global download progress dictionary"""
    return download_progress


def clear_download_progress() -> None:
    """Clear all download progress (useful for testing)"""
    global download_progress
    download_progress.clear()


def cancel_download_task(task_id: str) -> bool:
    """Cancel a download task by adding it to the cancelled tasks set"""
    global cancelled_tasks
    
    # Check if task exists in progress
    if task_id in download_progress:
        cancelled_tasks.add(task_id)
        
        # Update the task status to 'failed' with cancellation message
        if task_id in download_progress:
            download_progress[task_id]['status'] = 'failed'
            download_progress[task_id]['error_message'] = 'Download cancelled by user'
        
        logger.info(f"Download task {task_id} marked for cancellation")
        return True
    
    return False


def is_task_cancelled(task_id: str) -> bool:
    """Check if a task has been cancelled"""
    return task_id in cancelled_tasks


def remove_cancelled_task(task_id: str) -> None:
    """Remove a task from the cancelled tasks set (cleanup)"""
    global cancelled_tasks
    cancelled_tasks.discard(task_id)
