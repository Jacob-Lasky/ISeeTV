"""Scheduler integration module for ISeeTV FastAPI application.

This module provides atomic integration between the RefreshScheduler and
the existing FastAPI download/ingest endpoints.
"""

import json
import logging
import os
from typing import Any

from common.constants import DATA_PATH
from common.task_manager import DownloadTaskManager, IngestTaskManager
from common.utils import create_task_id, log_function
from download.downloader import background_single_download_task
from models.models import Source
from scheduler.job_queue_callbacks import refresh_job_callback_wrapper
from scheduler.refresh_scheduler import RefreshScheduler, validate_source_refresh_config

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Atomic manager for scheduler lifecycle and integration.

    Follows atomic design principles:
    - Single responsibility: manages scheduler lifecycle only
    - Modular: integrates with existing FastAPI endpoints
    - Scalable: handles unlimited sources efficiently
    """

    def __init__(self):
        self.scheduler: RefreshScheduler = None
        self._is_running = False
        log_function("SchedulerManager initialized")

    def initialize(self, download_callback, ingest_callback, sources_file: str) -> None:
        """Initialize the scheduler with callback functions.

        Args:
            download_callback: Async function to trigger downloads
            ingest_callback: Async function to trigger ingestion
            sources_file: Path to sources configuration file

        """
        log_function("Initializing scheduler with callbacks")
        self.scheduler = RefreshScheduler(
            download_callback=download_callback,
            ingest_callback=ingest_callback,
            sources_file=sources_file,
        )

    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized")

        if self._is_running:
            logger.warning("Scheduler already running")
            return

        log_function("Starting scheduler")
        self.scheduler.start()
        self.scheduler.schedule_all_sources()
        self._is_running = True
        log_function("Scheduler started and sources scheduled")

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self._is_running or not self.scheduler:
            return

        log_function("Stopping scheduler")
        self.scheduler.shutdown(wait=True)
        self._is_running = False
        log_function("Scheduler stopped")

    def restart(self) -> None:
        """Restart the scheduler."""
        log_function("Restarting scheduler")
        self.stop()
        self.start()

    def update_source_schedule(self, source: Source) -> None:
        """Update schedule for a specific source.

        Args:
            source: Updated source object

        """
        if not self.scheduler:
            logger.warning("Scheduler not initialized, cannot update source schedule")
            return

        log_function(f"Updating schedule for source: {source.name}")
        self.scheduler.update_source_schedule(source)

    def get_scheduler_status(self) -> dict[str, Any]:
        """Get current scheduler status and job information.

        Returns:
            Dictionary with scheduler status and job details

        """
        if not self.scheduler:
            return {"running": False, "initialized": False, "jobs": []}

        return {
            "running": self._is_running,
            "initialized": True,
            "jobs": self.scheduler.get_scheduled_jobs(),
        }

    def validate_and_schedule_sources(self, sources: list[Source]) -> dict[str, Any]:
        """Validate source configurations and schedule valid ones.

        Args:
            sources: List of source objects to validate and schedule

        Returns:
            Dictionary with validation results and scheduling status

        """
        results = {
            "valid_sources": [],
            "invalid_sources": [],
            "scheduled_count": 0,
            "errors": [],
        }

        for source in sources:
            if not source.enabled:
                continue

            validation_errors = validate_source_refresh_config(source)

            if validation_errors:
                results["invalid_sources"].append(
                    {"name": source.name, "errors": validation_errors}
                )
            else:
                results["valid_sources"].append(source.name)

                if self.scheduler:
                    try:
                        self.scheduler.schedule_source_refresh(source)
                        results["scheduled_count"] += 1
                    except Exception as e:
                        results["errors"].append(
                            f"Failed to schedule {source.name}: {e}"
                        )

        return results


# Global scheduler manager instance
scheduler_manager = SchedulerManager()


# Atomic callback functions for scheduler integration


async def download_callback_wrapper(source_name: str, file_type: str) -> None:
    """Wrapper function to trigger download via existing endpoint logic.

    This function replicates the core logic from queue_file_for_download
    without the HTTP response handling.

    Args:
        source_name: Name of the source
        file_type: Type of file to download

    """
    log_function(f"Scheduler triggering download: {source_name} {file_type}")

    try:
        # Create task ID
        task_id = create_task_id(source_name, file_type, "download")

        # Create download task
        DownloadTaskManager.create_download_task(task_id, 1)

        # Start background download task
        sources_file = os.path.join(DATA_PATH, "sources.json")
        download_dir = os.path.join(DATA_PATH, "sources")

        await background_single_download_task(
            task_id, source_name, file_type, sources_file, download_dir
        )

        log_function(f"Scheduler download completed: {source_name} {file_type}")

    except Exception as e:
        logger.error(f"Scheduler download failed for {source_name} {file_type}: {e}")
        raise


async def ingest_callback_wrapper(source_name: str, file_type: str) -> None:
    """Wrapper function to trigger ingest via existing endpoint logic.

    This function replicates the core logic from load_file_to_db
    without the HTTP response handling.

    Args:
        source_name: Name of the source
        file_type: Type of file to ingest

    """
    log_function(f"Scheduler triggering ingest: {source_name} {file_type}")

    try:
        # Load sources configuration
        sources_file = os.path.join(DATA_PATH, "sources.json")
        with open(sources_file) as f:
            sources = [Source(**source) for source in json.load(f)]

        # Find the source
        source = next(
            (source for source in sources if source.name == source_name), None
        )
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        # Get file metadata
        file_metadata = source.get_file_metadata(file_type)
        if not file_metadata or not file_metadata.local_path:
            raise ValueError(
                f"No {file_type.upper()} file defined for source '{source_name}'"
            )

        file_path = file_metadata.local_path

        if not os.path.exists(file_path):
            raise ValueError(f"File '{file_path}' not found for source '{source_name}'")

        # Create task ID and initialize task
        task_id = create_task_id(source_name, file_type, "ingest")

        # Extract total records for progress tracking
        total_records = 0
        if file_metadata.total_records:
            if file_type == "m3u":
                total_records = file_metadata.total_records.channels or 0
                total_steps = 3  # download, parse, load
            elif file_type == "epg":
                # For EPG, use channels + programs
                channels = file_metadata.total_records.channels or 0
                programs = file_metadata.total_records.programs or 0
                total_records = channels + programs
                total_steps = 5  # download, parse channels, load channels, parse programs, load programs

        IngestTaskManager.create_ingest_task(
            task_id, file_type, source_name, total_records, total_steps
        )

        # Start background load task
        from main import background_load_task

        await background_load_task(task_id, file_type, file_path, source_name)

        log_function(f"Scheduler ingest completed: {source_name} {file_type}")

    except Exception as e:
        logger.error(f"Scheduler ingest failed for {source_name} {file_type}: {e}")
        raise


# Atomic utility functions


def get_scheduler_manager() -> SchedulerManager:
    """Get the global scheduler manager instance."""
    return scheduler_manager


def initialize_scheduler(sources_file: str) -> None:
    """Initialize the global scheduler with job queue integration.

    Args:
        sources_file: Path to sources configuration file

    """
    log_function("Initializing global scheduler with job queue integration")

    scheduler_manager.initialize(
        download_callback=refresh_job_callback_wrapper,
        ingest_callback=refresh_job_callback_wrapper,
        sources_file=sources_file,
    )


def start_scheduler() -> None:
    """Start the global scheduler."""
    scheduler_manager.start()


def stop_scheduler() -> None:
    """Stop the global scheduler."""
    scheduler_manager.stop()
