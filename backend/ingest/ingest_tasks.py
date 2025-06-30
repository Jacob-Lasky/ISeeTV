"""
Ingest task management for ISeeTV ETL pipeline.
 functions for creating and updating ingest progress tracking.
"""

import datetime as dt
from typing import Dict, Optional
from common.state import get_progress


def create_ingest_task(
    task_id: str, file_type: str, total_items: int, source_name: str
) -> None:
    """Create a new ingest task in progress tracking"""
    ingest_progress = get_progress("ingest")
    ingest_progress[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "file_type": file_type,
        "current_item": None,
        "total_items": total_items,
        "completed_items": 0,
        "error_message": None,
        "started_at": dt.datetime.now(dt.timezone.utc),
        "completed_at": None,
        "source_name": source_name,  # Additional context
        "current_phase": None,  # For EPG: "channels" or "programs"
    }


def update_ingest_progress(task_id: str, **kwargs) -> None:
    """Update ingest progress"""
    ingest_progress = get_progress("ingest")
    if task_id in ingest_progress:
        # Update timestamp for any progress update
        kwargs["updated_at"] = dt.datetime.now(dt.timezone.utc)
        ingest_progress[task_id].update(kwargs)


def start_ingest_task(task_id: str) -> None:
    """Mark ingest task as started"""
    update_ingest_progress(
        task_id, status="ingesting", started_at=dt.datetime.now(dt.timezone.utc)
    )


def complete_ingest_task(task_id: str, message: Optional[str] = None) -> None:
    """Mark ingest task as completed"""
    update_ingest_progress(
        task_id,
        status="completed",
        completed_at=dt.datetime.now(dt.timezone.utc),
        current_item=message or "Completed successfully",
    )


def fail_ingest_task(task_id: str, error_message: str) -> None:
    """Mark ingest task as failed"""
    update_ingest_progress(
        task_id,
        status="failed",
        error_message=error_message,
        completed_at=dt.datetime.now(dt.timezone.utc),
    )


def update_ingest_item_progress(
    task_id: str,
    current_item: str,
    completed_items: int,
    current_phase: Optional[str] = None,
) -> None:
    """Update current item being processed"""
    kwargs = {"current_item": current_item, "completed_items": completed_items}
    if current_phase:
        kwargs["current_phase"] = current_phase

    update_ingest_progress(task_id, **kwargs)


def get_ingest_task(task_id: str) -> Optional[Dict]:
    """Get a specific ingest task"""
    ingest_progress = get_progress("ingest")
    return ingest_progress.get(task_id)
