"""
APScheduler + asyncio refresh scheduling system for ISeeTV sources.

This module provides atomic, modular scheduling functionality that integrates
with existing download and ingest flows in main.py.
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal, Callable, Any
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, JobExecutionEvent

from models.models import Source
from common.utils import log_function
from common.constants import DATA_PATH

logger = logging.getLogger(__name__)


class RefreshScheduler:
    """
    Atomic scheduler for Source refresh operations.

    Follows atomic design principles:
    - Single responsibility: manages scheduled refreshes only
    - Modular: integrates with existing download/ingest flows
    - Scalable: handles unlimited sources with efficient job management
    """

    def __init__(
        self,
        download_callback: Callable[[str, Literal["m3u", "epg"]], Any],
        ingest_callback: Callable[[str, Literal["m3u", "epg"]], Any],
        sources_file: str = os.path.join(DATA_PATH, "sources.json"),
    ):
        """
        Initialize the refresh scheduler.

        Args:
            download_callback: Async function to trigger downloads (e.g., queue_file_for_download)
            ingest_callback: Async function to trigger ingestion (e.g., load_file_to_db)
            sources_file: Path to sources configuration file
        """
        self.scheduler = AsyncIOScheduler()
        self.download_callback = download_callback
        self.ingest_callback = ingest_callback
        self.sources_file = sources_file
        self._job_registry: Dict[str, List[str]] = {}  # source_name -> [job_ids]

        # Configure scheduler event listeners
        self.scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)

        log_function("RefreshScheduler initialized")

    def start(self) -> None:
        """Start the scheduler."""
        log_function("Starting RefreshScheduler")
        self.scheduler.start()

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler."""
        log_function("Shutting down RefreshScheduler")
        self.scheduler.shutdown(wait=wait)

    def load_sources(self) -> List[Source]:
        """
        Load sources from configuration file.

        Returns:
            List of Source objects
        """
        try:
            with open(self.sources_file, "r") as f:
                sources_data = json.load(f)
            return [Source(**source) for source in sources_data]
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error loading sources from {self.sources_file}: {e}")
            return []

    def schedule_all_sources(self) -> None:
        """
        Schedule refresh jobs for all enabled sources.

        This is the main entry point for setting up all scheduled refreshes.
        """
        log_function("Scheduling all sources")
        sources = self.load_sources()

        for source in sources:
            if source.enabled:
                self.schedule_source_refresh(source)
            else:
                log_function(f"Skipping disabled source: {source.name}")

    def schedule_source_refresh(self, source: Source) -> None:
        """
        Schedule refresh jobs for a single source.

        Args:
            source: Source object to schedule
        """
        log_function(f"Scheduling refresh for source: {source.name}")

        # Remove existing jobs for this source
        self.remove_source_jobs(source.name)

        # Skip if refresh is not configured
        if not source.refresh_every_hours or not source.refresh_time:
            log_function(f"Source {source.name} has no refresh configuration, skipping")
            return

        # Calculate next refresh times for each file type
        file_types = ["m3u", "epg"]
        job_ids = []

        for file_type in file_types:
            file_metadata = source.get_file_metadata(file_type)
            if file_metadata and file_metadata.url:
                job_id = self._schedule_file_refresh(source, file_type)
                if job_id:
                    job_ids.append(job_id)

        # Register jobs for this source
        if job_ids:
            self._job_registry[source.name] = job_ids
            log_function(
                f"Scheduled {len(job_ids)} refresh jobs for source {source.name}"
            )

    def _schedule_file_refresh(
        self, source: Source, file_type: Literal["m3u", "epg"]
    ) -> Optional[str]:
        """
        Schedule refresh for a specific file type of a source.

        Args:
            source: Source object
            file_type: Type of file to refresh

        Returns:
            Job ID if scheduled successfully, None otherwise
        """
        try:
            # Calculate next refresh datetime
            next_refresh = self._calculate_next_refresh(source)
            if not next_refresh:
                return None

            # Create job ID
            job_id = f"refresh_{source.name}_{file_type}"

            # Create cron trigger for recurring refresh
            trigger = self._create_cron_trigger(source)

            # Schedule the job
            job = self.scheduler.add_job(
                func=self._refresh_file_job,
                trigger=trigger,
                args=[source.name, file_type],
                id=job_id,
                name=f"Refresh {file_type.upper()} for {source.name}",
                next_run_time=next_refresh,
                replace_existing=True,
            )

            log_function(
                f"Scheduled {file_type} refresh for {source.name} at {next_refresh}"
            )
            return job_id

        except Exception as e:
            logger.error(f"Error scheduling {file_type} refresh for {source.name}: {e}")
            return None

    def _calculate_next_refresh(self, source: Source) -> Optional[datetime]:
        """
        Calculate the next refresh datetime for a source.

        Args:
            source: Source object

        Returns:
            Next refresh datetime or None if invalid configuration
        """
        if not source.refresh_time or not source.refresh_every_hours:
            return None

        try:
            # Parse refresh time (HH:MM format)
            hour, minute = map(int, source.refresh_time.split(":"))

            # Get timezone (default to UTC if not specified)
            tz = (
                ZoneInfo(source.source_timezone)
                if source.source_timezone
                else ZoneInfo("UTC")
            )

            # Get current time in source timezone
            now = datetime.now(tz)

            # Calculate next refresh time
            next_refresh = now.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )

            # If the time has already passed today, move to next occurrence
            if next_refresh <= now:
                next_refresh += timedelta(hours=source.refresh_every_hours)

            log_function(f"Next refresh for {source.name}: {next_refresh} ({tz})")
            return next_refresh

        except (ValueError, Exception) as e:
            logger.error(f"Error calculating next refresh for {source.name}: {e}")
            return None

    def _create_cron_trigger(self, source: Source):
        """
        Create a trigger for recurring refresh.

        Args:
            source: Source object

        Returns:
            Trigger for the source's refresh schedule (CronTrigger or IntervalTrigger)
        """
        hour, minute = map(int, source.refresh_time.split(":"))
        tz = (
            ZoneInfo(source.source_timezone)
            if source.source_timezone
            else ZoneInfo("UTC")
        )

        # For intervals >= 24 hours, use IntervalTrigger
        if source.refresh_every_hours >= 24:
            return IntervalTrigger(hours=source.refresh_every_hours, timezone=tz)

        # For intervals < 24 hours, use CronTrigger with proper hour expression
        if source.refresh_every_hours == 1:
            # Every hour at the specified minute
            hour_expr = "*"
        elif 24 % source.refresh_every_hours == 0:
            # Evenly divisible intervals (2, 3, 4, 6, 8, 12 hours)
            hour_values = []
            for h in range(0, 24, source.refresh_every_hours):
                hour_values.append(str(h))
            hour_expr = ",".join(hour_values)
        else:
            # Non-evenly divisible intervals, use IntervalTrigger
            return IntervalTrigger(hours=source.refresh_every_hours, timezone=tz)

        return CronTrigger(hour=hour_expr, minute=minute, timezone=tz)

    async def _refresh_file_job(
        self, source_name: str, file_type: Literal["m3u", "epg"]
    ) -> None:
        """
        Execute refresh job for a specific file.

        This is the atomic job function that orchestrates download + ingest.

        Args:
            source_name: Name of the source
            file_type: Type of file to refresh
        """
        log_function(f"Executing refresh job for {source_name} {file_type}")

        try:
            # Step 1: Download the file
            log_function(f"Starting download for {source_name} {file_type}")
            await self.download_callback(source_name, file_type)

            # Step 2: Wait a moment for download to complete
            # In a production system, you might want to monitor the download task status
            await asyncio.sleep(5)

            # Step 3: Ingest the file to database
            log_function(f"Starting ingest for {source_name} {file_type}")
            await self.ingest_callback(source_name, file_type)

            log_function(f"Completed refresh job for {source_name} {file_type}")

        except Exception as e:
            logger.error(f"Error in refresh job for {source_name} {file_type}: {e}")
            raise

    def remove_source_jobs(self, source_name: str) -> None:
        """
        Remove all scheduled jobs for a source.

        Args:
            source_name: Name of the source
        """
        if source_name in self._job_registry:
            for job_id in self._job_registry[source_name]:
                try:
                    self.scheduler.remove_job(job_id)
                    log_function(f"Removed job {job_id}")
                except Exception as e:
                    logger.warning(f"Error removing job {job_id}: {e}")

            del self._job_registry[source_name]

    def update_source_schedule(self, source: Source) -> None:
        """
        Update the schedule for a specific source.

        Args:
            source: Updated source object
        """
        log_function(f"Updating schedule for source: {source.name}")
        self.schedule_source_refresh(source)

    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """
        Get information about all scheduled jobs.

        Returns:
            List of job information dictionaries
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": (
                        job.next_run_time.isoformat() if job.next_run_time else None
                    ),
                    "trigger": str(job.trigger),
                }
            )
        return jobs

    def _on_job_executed(self, event: JobExecutionEvent) -> None:
        """Handle successful job execution."""
        log_function(f"Job {event.job_id} executed successfully")

    def _on_job_error(self, event: JobExecutionEvent) -> None:
        """Handle job execution errors."""
        logger.error(f"Job {event.job_id} failed: {event.exception}")


# Utility functions for atomic time calculations


def parse_refresh_time(refresh_time: str) -> tuple[int, int]:
    """
    Parse refresh time string into hour and minute.

    Args:
        refresh_time: Time string in HH:MM format

    Returns:
        Tuple of (hour, minute)

    Raises:
        ValueError: If time format is invalid
    """
    try:
        hour, minute = map(int, refresh_time.split(":"))
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            raise ValueError("Invalid time values")
        return hour, minute
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid refresh_time format '{refresh_time}': {e}")


def calculate_next_occurrence(
    base_time: datetime,
    refresh_time: str,
    interval_hours: int,
    timezone: Optional[str] = None,
) -> datetime:
    """
    Calculate the next occurrence of a refresh time.

    Args:
        base_time: Base datetime to calculate from
        refresh_time: Target time in HH:MM format
        interval_hours: Interval between refreshes in hours
        timezone: Timezone string (optional)

    Returns:
        Next occurrence datetime
    """
    hour, minute = parse_refresh_time(refresh_time)
    tz = ZoneInfo(timezone) if timezone else base_time.tzinfo

    # Convert base time to target timezone
    if tz and base_time.tzinfo != tz:
        base_time = base_time.astimezone(tz)

    # Calculate target time today
    target_time = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If target time has passed, calculate next occurrence
    while target_time <= base_time:
        target_time += timedelta(hours=interval_hours)

    return target_time


def validate_source_refresh_config(source: Source) -> List[str]:
    """
    Validate source refresh configuration.

    Args:
        source: Source object to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not source.refresh_every_hours:
        errors.append("refresh_every_hours is required")
    elif source.refresh_every_hours <= 0:
        errors.append("refresh_every_hours must be positive")

    if not source.refresh_time:
        errors.append("refresh_time is required")
    else:
        try:
            parse_refresh_time(source.refresh_time)
        except ValueError as e:
            errors.append(f"Invalid refresh_time: {e}")

    if source.source_timezone:
        try:
            ZoneInfo(source.source_timezone)
        except Exception:
            errors.append(f"Invalid timezone: {source.source_timezone}")

    return errors
