"""APScheduler + asyncio refresh scheduling system for ISeeTV sources.

This module provides atomic, modular scheduling functionality that integrates
with existing download and ingest flows in main.py.
"""

import asyncio
import json
import os
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobExecutionEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from common.constants import DATA_PATH
from common.log_utils import get_logger
from models.models import Source

logger = get_logger(__name__)


class RefreshScheduler:
    """Atomic scheduler for Source refresh operations.

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
        """Initialize the refresh scheduler.

        Args:
            download_callback: Async function to trigger downloads (e.g., queue_file_for_download)
            ingest_callback: Async function to trigger ingestion (e.g., load_file_to_db)
            sources_file: Path to sources configuration file

        """
        self.scheduler = AsyncIOScheduler()
        self.download_callback = download_callback
        self.ingest_callback = ingest_callback
        self.sources_file = sources_file
        self._job_registry: dict[str, list[str]] = {}  # source_name -> [job_ids]

        # Configure scheduler event listeners
        self.scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)

        logger.debug("RefreshScheduler initialized")

    def start(self) -> None:
        """Start the scheduler."""
        logger.debug("Starting RefreshScheduler")
        self.scheduler.start()

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler."""
        logger.debug("Shutting down RefreshScheduler")
        self.scheduler.shutdown(wait=wait)

    def load_sources(self) -> list[Source]:
        """Load sources from configuration file.

        Returns:
            List of Source objects

        """
        logger.info("Loading sources from %s", self.sources_file)
        try:
            with open(self.sources_file) as f:
                sources_data = json.load(f)
            return [Source(**source) for source in sources_data]
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            logger.exception("Error loading sources from %s", self.sources_file)
            return []

    def schedule_all_sources(self) -> None:
        """Schedule refresh jobs for all enabled sources.

        This is the main entry point for setting up all scheduled refreshes.
        """
        logger.info("Scheduling all sources")
        sources = self.load_sources()

        for source in sources:
            if source.enabled:
                self.schedule_source_refresh(source)
            else:
                logger.info("Skipping disabled source: %s", source.name)

    def schedule_source_refresh(self, source: Source) -> None:
        """Schedule refresh jobs for a single source.

        Args:
            source: Source object to schedule

        """
        logger.info("Scheduling refresh for source: %s", source.name)

        # Remove existing jobs for this source
        self.remove_source_jobs(source.name)

        # Skip if refresh is not configured
        if not source.refresh_every_hours or not source.refresh_time:
            logger.info("Source %s has no refresh configuration, skipping", source.name)
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
            logger.debug(
                "Scheduled %s refresh jobs for source %s",
                len(job_ids),
                source.name,
            )

    def _schedule_file_refresh(
        self, source: Source, file_type: Literal["m3u", "epg"]
    ) -> str | None:
        """Schedule refresh for a specific file type of a source.

        Args:
            source: Source object
            file_type: Type of file to refresh

        Returns:
            Job ID if scheduled successfully, None otherwise

        """
        logger.debug("Scheduling %s refresh for source %s", file_type, source.name)
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

            logger.info(
                "Scheduled %s refresh for %s at %s",
                file_type,
                source.name,
                next_refresh,
            )
            return job_id

        except Exception:
            logger.exception(
                "Error scheduling %s refresh for %s", file_type, source.name
            )
            return None

    def _calculate_next_refresh(self, source: Source) -> datetime | None:
        """Calculate the next refresh datetime for a source.

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

            logger.debug("Next refresh for %s: %s (%s)", source.name, next_refresh, tz)
            return next_refresh

        except (ValueError, Exception):
            logger.exception("Error calculating next refresh for %s", source.name)
            return None

    def _create_cron_trigger(self, source: Source):
        """Create a trigger for recurring refresh.

        Args:
            source: Source object

        Returns:
            Trigger for the source's refresh schedule (CronTrigger or IntervalTrigger)

        """
        logger.debug("Creating cron trigger for %s", source.name)
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
        """Execute refresh job for a specific file.

        This is the atomic job function that orchestrates download + ingest.

        Args:
            source_name: Name of the source
            file_type: Type of file to refresh

        """
        logger.info("Executing refresh job for %s %s", source_name, file_type)

        try:
            # Step 1: Download the file
            logger.info("Starting download for %s %s", source_name, file_type)
            await self.download_callback(source_name, file_type)

            # Step 2: Wait a moment for download to complete
            # In a production system, you might want to monitor the download task status
            await asyncio.sleep(5)

            # Step 3: Ingest the file to database
            logger.info("Starting ingest for %s %s", source_name, file_type)
            await self.ingest_callback(source_name, file_type)

            logger.info("Completed refresh job for %s %s", source_name, file_type)

        except Exception:
            logger.exception("Error in refresh job for %s %s", source_name, file_type)
            raise

    def remove_source_jobs(self, source_name: str) -> None:
        """Remove all scheduled jobs for a source.

        Args:
            source_name: Name of the source

        """
        if source_name in self._job_registry:
            for job_id in self._job_registry[source_name]:
                try:
                    self.scheduler.remove_job(job_id)
                    logger.info("Removed job %s", job_id)
                except Exception:
                    logger.warning("Error removing job %s", job_id)

            del self._job_registry[source_name]

    def update_source_schedule(self, source: Source) -> None:
        """Update the schedule for a specific source.

        Args:
            source: Updated source object

        """
        logger.info("Updating schedule for source: %s", source.name)
        self.schedule_source_refresh(source)

    def get_scheduled_jobs(self) -> list[dict[str, Any]]:
        """Get information about all scheduled jobs.

        Returns:
            List of job information dictionaries

        """
        logger.info("Getting scheduled jobs")
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
        logger.info("Job %s executed successfully", event.job_id)

    def _on_job_error(self, event: JobExecutionEvent) -> None:
        """Handle job execution errors."""
        logger.error("Job %s failed: %s", event.job_id, event.exception)


# Utility functions for atomic time calculations


def parse_refresh_time(refresh_time: str) -> tuple[int, int]:
    """Parse refresh time string into hour and minute.

    Args:
        refresh_time: Time string in HH:MM format

    Returns:
        Tuple of (hour, minute)

    Raises:
        ValueError: If time format is invalid

    """
    logger.info("Parsing refresh time: %s", refresh_time)
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
    timezone: str | None = None,
) -> datetime:
    """Calculate the next occurrence of a refresh time.

    Args:
        base_time: Base datetime to calculate from
        refresh_time: Target time in HH:MM format
        interval_hours: Interval between refreshes in hours
        timezone: Timezone string (optional)

    Returns:
        Next occurrence datetime

    """
    logger.info("Calculating next occurrence for %s %s", refresh_time, interval_hours)
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


def validate_source_refresh_config(source: Source) -> list[str]:
    """Validate source refresh configuration.

    Args:
        source: Source object to validate

    Returns:
        List of validation error messages (empty if valid)

    """
    logger.info("Validating source refresh config for %s", source.name)
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
