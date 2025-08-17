"""Generalized task management system for ISeeTV following atomic design principles.
Provides shared utilities for managing download and ingest tasks with DRY compliance.
"""

import datetime as dt
from typing import Any, Literal

from common.log_utils import get_logger
from common.state import get_progress

logger = get_logger(__name__)

TASK_TYPES = Literal["download", "ingest", "indexing"]


class TaskManager:
    """Task management utilities for both download and ingest tasks."""

    @staticmethod
    def create_task(
        task_id: str,
        task_type: TASK_TYPES,
        base_fields: dict[str, Any],
        **additional_fields,
    ) -> None:
        """Create a new task with base fields and task-type-specific fields.

        Args:
            task_id: Unique identifier for the task
            task_type: Type of task (download or ingest)
            base_fields: Common fields for all tasks
            **additional_fields: Task-type-specific fields

        """
        logger.debug("Creating %s task %s", task_type, task_id)

        # Base task structure shared by all task types
        task_data = {
            "task_id": task_id,
            "status": "pending",
            "current_item": None,
            "total_items": 0,
            "completed_items": 0,
            "error_message": None,
            "started_at": dt.datetime.now(dt.UTC),
            "completed_at": None,
            "updated_at": dt.datetime.now(dt.UTC),
            **base_fields,
            **additional_fields,
        }

        # Store in appropriate progress tracker
        progress = get_progress(task_type)
        progress[task_id] = task_data

    @staticmethod
    def update_task_progress(task_id: str, task_type: TASK_TYPES, **kwargs) -> None:
        """Update task progress with automatic timestamp tracking.

        Args:
            task_id: Task identifier
            task_type: Type of task
            **kwargs: Fields to update

        """
        logger.debug("Updating %s task %s progress: %s", task_type, task_id, kwargs)
        progress = get_progress(task_type)
        if task_id in progress:
            # Always update timestamp on any progress change
            kwargs["updated_at"] = dt.datetime.now(dt.UTC)
            progress[task_id].update(kwargs)

    @staticmethod
    def start_task(
        task_id: str, task_type: TASK_TYPES, status_name: str | None = None
    ) -> None:
        """Mark task as started with appropriate status.

        Args:
            task_id: Task identifier
            task_type: Type of task
            status_name: Custom status name (defaults to task_type + "ing")

        """
        status = status_name or f"{task_type}ing"
        logger.debug("Starting %s task %s", task_type, task_id)

        TaskManager.update_task_progress(
            task_id,
            task_type,
            status=status,
            started_at=dt.datetime.now(dt.UTC),
        )

    @staticmethod
    def complete_task(
        task_id: str, task_type: TASK_TYPES, message: str | None = None
    ) -> None:
        """Mark task as completed successfully.

        Args:
            task_id: Task identifier
            task_type: Type of task
            message: Optional completion message

        """
        logger.info("Completing %s task %s", task_type, task_id)

        update_data = {
            "status": "completed",
            "completed_at": dt.datetime.now(dt.UTC),
        }

        if message:
            update_data["current_item"] = message

        TaskManager.update_task_progress(task_id, task_type, **update_data)

    @staticmethod
    def fail_task(task_id: str, task_type: TASK_TYPES, error_message: str) -> None:
        """Mark task as failed with error message.

        Args:
            task_id: Task identifier
            task_type: Type of task
            error_message: Error description

        """
        logger.info("Failing %s task %s", task_type, task_id)

        TaskManager.update_task_progress(
            task_id,
            task_type,
            status="failed",
            error_message=error_message,
            completed_at=dt.datetime.now(dt.UTC),
        )

    @staticmethod
    def get_task(
        task_id: str,
        task_type: TASK_TYPES,
    ) -> dict[str, Any] | None:
        """Get a specific task by ID and type.

        Args:
            task_id: Task identifier
            task_type: Type of task

        Returns:
            Task data dictionary or None if not found

        """
        logger.debug("Getting %s task %s", task_type, task_id)
        progress = get_progress(task_type)
        return progress.get(task_id)

    @staticmethod
    def update_total_items(
        task_id: str, task_type: TASK_TYPES, total_items: int
    ) -> None:
        """Update the total_items count for a task after parsing determines actual count.

        Args:
            task_id: Task identifier
            task_type: Type of task
            total_items: Actual total number of items to process

        """
        logger.debug(
            "Updating %s task %s total_items to %s", task_type, task_id, total_items
        )

        TaskManager.update_task_progress(task_id, task_type, total_items=total_items)

    @staticmethod
    def update_item_progress(
        task_id: str,
        task_type: TASK_TYPES,
        current_item: str,
        completed_items: int,
        **additional_fields,
    ) -> None:
        """Update progress for a specific item in a task.

        Args:
            task_id: Task identifier
            task_type: Type of task
            current_item: Description of current item being processed
            completed_items: Number of items completed
            **additional_fields: Additional fields to update

        """
        logger.debug(
            "Updating %s task %s item progress: %s",
            task_type,
            task_id,
            completed_items,
        )
        TaskManager.update_task_progress(
            task_id,
            task_type,
            current_item=current_item,
            completed_items=completed_items,
            **additional_fields,
        )


class DownloadTaskManager:
    """Specialized task manager for download tasks with byte-level progress tracking.
    Extends the base TaskManager with download-specific functionality.
    """

    @staticmethod
    def create_download_task(
        task_id: str, total_items: int, file_type: str | None = None
    ) -> None:
        """Create a new download task with download-specific fields."""
        logger.debug("Creating download task %s", task_id)
        download_fields = {
            "bytes_downloaded": 0,
            "total_bytes": 0,
            "file_type": file_type,
        }

        # Use ISO format for download tasks (legacy compatibility)
        base_fields = {
            "total_items": total_items,
            "started_at": dt.datetime.now(dt.UTC).isoformat(),
        }

        TaskManager.create_task(task_id, "download", base_fields, **download_fields)

    @staticmethod
    def update_download_progress(task_id: str, **kwargs) -> None:
        """Update download progress with automatic timestamp handling."""
        logger.debug("Updating download task %s progress: %s", task_id, kwargs)
        # Convert datetime to ISO format for download tasks (legacy compatibility)
        if "completed_at" in kwargs and isinstance(kwargs["completed_at"], dt.datetime):
            kwargs["completed_at"] = kwargs["completed_at"].isoformat()
        if "started_at" in kwargs and isinstance(kwargs["started_at"], dt.datetime):
            kwargs["started_at"] = kwargs["started_at"].isoformat()

        TaskManager.update_task_progress(task_id, "download", **kwargs)


class IngestTaskManager:
    """Specialized task manager for ingest tasks with multi-step progress tracking.
    Extends the base TaskManager with ingest-specific functionality.
    """

    @staticmethod
    def create_ingest_task(
        task_id: str,
        file_type: str,
        source_name: str,
        total_items: int = 0,
        total_steps: int = 3,
    ) -> None:
        """Create a new ingest task with multi-step progress tracking."""
        logger.debug("Creating ingest task %s", task_id)
        ingest_fields = {
            "file_type": file_type,
            "source_name": source_name,
            "current_phase": None,  # For EPG: "channels" or "programs"
            # Multi-step progress tracking
            "current_step": 1,
            "total_steps": total_steps,  # Download, Parse, Load (+Parse, +Load for EPG)
            "step_name": "downloading",
            "step_progress": 0,  # Progress within current step (0-100)
            "overall_progress": 0,  # Overall progress across all steps (0-100)
        }

        base_fields = {
            "total_items": total_items,
        }

        TaskManager.create_task(task_id, "ingest", base_fields, **ingest_fields)

    @staticmethod
    def update_step_progress(
        task_id: str,
        step: int,
        step_name: str,
        step_progress: int,
        total_steps: int = 3,
    ) -> None:
        """Update progress for current step in multi-step ingest process."""
        logger.debug(
            "Updating ingest task %s step progress: %s", task_id, step_progress
        )
        # Calculate overall progress (each step is 1/3 of total)
        base_progress = ((step - 1) / total_steps) * 100
        step_contribution = (step_progress / 100) * (100 / total_steps)
        overall_progress = min(100, base_progress + step_contribution)

        TaskManager.update_task_progress(
            task_id,
            "ingest",
            current_step=step,
            step_name=step_name,
            step_progress=step_progress,
            overall_progress=overall_progress,
        )

    @staticmethod
    def update_item_progress(
        task_id: str,
        current_item: str,
        completed_items: int,
        current_phase: str | None = None,
    ) -> None:
        """Update progress for a specific item in an ingest task."""
        logger.debug("Updating ingest task %s item progress: %s", task_id, current_item)
        additional_fields = {}
        if current_phase:
            additional_fields["current_phase"] = current_phase

        TaskManager.update_item_progress(
            task_id, "ingest", current_item, completed_items, **additional_fields
        )

        # Update step progress if we have total items
        task = TaskManager.get_task(task_id, "ingest")
        if task and task.get("total_items", 0) > 0:
            step_progress = min(100, (completed_items / task["total_items"]) * 100)
            current_step = task.get(
                "current_step", task.get("total_steps", 3)
            )  # Default to loading step
            step_name = task.get("step_name", "loading")
            IngestTaskManager.update_step_progress(
                task_id,
                current_step,
                step_name,
                step_progress,
                task.get("total_steps", 3),
            )


class IndexingTaskManager:
    """Specialized task manager for indexing tasks.
    Provides helpers to create and update indexing progress.
    """

    @staticmethod
    def create_indexing_task(
        task_id: str,
        index_name: str,
        source_name: str | None = None,
        total_items: int = 0,
    ) -> None:
        """Create a new indexing task with indexing-specific fields."""
        logger.debug("Creating indexing task %s for index %s", task_id, index_name)
        indexing_fields = {
            "index_name": index_name,
            "source_name": source_name,
        }

        base_fields = {
            "total_items": total_items,
        }

        TaskManager.create_task(task_id, "indexing", base_fields, **indexing_fields)

    @staticmethod
    def update_item_progress(
        task_id: str,
        processed_items: int,
        current_item: str = "",
    ) -> None:
        """Update progress for a specific item in an indexing task."""
        logger.debug("Updating indexing task %s item progress: %d processed", task_id, processed_items)
        TaskManager.update_item_progress(
            task_id, "indexing", current_item, processed_items
        )

    @staticmethod
    def complete_task(task_id: str) -> None:
        """Mark an indexing task as completed."""
        logger.debug("Completing indexing task %s", task_id)
        TaskManager.complete_task(task_id, "indexing")

    @staticmethod
    def fail_task(task_id: str, error_message: str) -> None:
        """Mark an indexing task as failed."""
        logger.debug("Failing indexing task %s: %s", task_id, error_message)
        TaskManager.fail_task(task_id, "indexing", error_message)
