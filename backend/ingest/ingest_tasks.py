"""
Ingest task management for ISeeTV ETL pipeline.
 functions for creating and updating ingest progress tracking.
"""

import datetime as dt
from typing import Dict, Optional
from common.state import get_progress
from common.utils import log_function


def create_ingest_task(
    task_id: str, file_type: str, source_name: str, total_items: int = 0
) -> None:
    """Create a new ingest task in progress tracking with multi-step support"""
    log_function(f"Creating ingest task {task_id}")
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
        "source_name": source_name,
        "current_phase": None,  # For EPG: "channels" or "programs"
        # Multi-step progress tracking
        "current_step": 1,
        "total_steps": 3,  # Download, Parse, Load
        "step_name": "downloading",
        "step_progress": 0,  # Progress within current step (0-100)
        "overall_progress": 0,  # Overall progress across all steps (0-100)
    }


def update_ingest_progress(task_id: str, **kwargs) -> None:
    """Update ingest progress"""
    ingest_progress = get_progress("ingest")
    if task_id in ingest_progress:
        # Update timestamp for any progress update
        kwargs["updated_at"] = dt.datetime.now(dt.timezone.utc)
        ingest_progress[task_id].update(kwargs)


def update_ingest_step_progress(
    task_id: str, step: int, step_name: str, step_progress: int
) -> None:
    """Update progress for current step in multi-step ingest process"""
    ingest_progress = get_progress("ingest")
    if task_id in ingest_progress:
        ingest_progress[task_id]["current_step"] = step
        ingest_progress[task_id]["step_name"] = step_name
        ingest_progress[task_id]["step_progress"] = step_progress
        ingest_progress[task_id]["updated_at"] = dt.datetime.now(dt.timezone.utc)

        # Calculate overall progress (each step is 1/3 of total)
        base_progress = ((step - 1) / 3) * 100
        step_contribution = (step_progress / 100) * (100 / 3)
        ingest_progress[task_id]["overall_progress"] = min(
            100, base_progress + step_contribution
        )


def update_ingest_item_progress(
    task_id: str, current_item: str, completed_items: int, current_phase: str = None
) -> None:
    """Update progress for a specific item in an ingest task"""
    ingest_progress = get_progress("ingest")
    if task_id in ingest_progress:
        ingest_progress[task_id]["current_item"] = current_item
        ingest_progress[task_id]["completed_items"] = completed_items
        ingest_progress[task_id]["updated_at"] = dt.datetime.now(dt.timezone.utc)
        if current_phase:
            ingest_progress[task_id]["current_phase"] = current_phase

        # Update step progress if we have total items
        total_items = ingest_progress[task_id].get("total_items", 0)
        if total_items > 0:
            step_progress = min(100, (completed_items / total_items) * 100)
            current_step = ingest_progress[task_id].get(
                "current_step", 3
            )  # Default to loading step
            step_name = ingest_progress[task_id].get("step_name", "loading")
            update_ingest_step_progress(task_id, current_step, step_name, step_progress)


def start_ingest_task(task_id: str) -> None:
    """Mark ingest task as started"""
    log_function(f"Starting ingest task {task_id}")
    update_ingest_progress(
        task_id, status="ingesting", started_at=dt.datetime.now(dt.timezone.utc)
    )


def complete_ingest_task(task_id: str, message: Optional[str] = None) -> None:
    """Mark ingest task as completed"""
    log_function(f"Completing ingest task {task_id}")
    update_ingest_progress(
        task_id,
        status="completed",
        completed_at=dt.datetime.now(dt.timezone.utc),
        current_item=message or "Completed successfully",
    )


def fail_ingest_task(task_id: str, error_message: str) -> None:
    """Mark ingest task as failed"""
    log_function(f"Failing ingest task {task_id}")
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
