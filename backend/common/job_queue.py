"""Global job queue system for ISeeTV to ensure single-job execution.

This module provides atomic, modular job queue functionality that ensures
only one job runs at a time across the entire application.
"""

import asyncio
import contextlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from common.log_utils import get_logger

logger = get_logger(__name__)


class JobStatus(Enum):
    """Atomic job status enumeration."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(Enum):
    """Atomic job type enumeration."""

    DOWNLOAD = "download"
    INGEST = "ingest"
    REFRESH = "refresh"
    BULK_DOWNLOAD = "bulk_download"
    INDEXING = "indexing"


@dataclass
class JobInfo:
    """Atomic job information container.

    Follows atomic design principles:
    - Single responsibility: contains job metadata only
    - Immutable: job info doesn't change after creation (except status)
    - Modular: can be extended with new fields without breaking existing code
    """

    job_id: str
    job_type: JobType
    source_name: str
    file_type: Literal["m3u", "epg"] | None = None
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    progress: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert job info to dictionary for API responses."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type.value,
            "source_name": self.source_name,
            "file_type": self.file_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "error_message": self.error_message,
            "progress": self.progress,
        }


class JobQueue:
    """Atomic global job queue manager.

    Follows atomic design principles:
    - Single responsibility: manages job queue and execution
    - Modular: integrates with existing job functions without modification
    - Scalable: handles unlimited job types and sources
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._jobs: dict[str, JobInfo] = {}
        self._current_job: JobInfo | None = None
        self._worker_task: asyncio.Task | None = None
        self._running = False
        self._lock = asyncio.Lock()

        logger.debug("JobQueue initialized")

    async def start(self) -> None:
        """Start the job queue worker."""
        if self._running:
            logger.warning("Job queue already running")
            return

        logger.debug("Starting job queue worker")
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        """Stop the job queue worker."""
        if not self._running:
            return

        logger.debug("Stopping job queue worker")
        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task

    async def enqueue_job(
        self,
        job_type: JobType,
        source_name: str,
        job_function: Callable,
        file_type: Literal["m3u", "epg"] | None = None,
        **kwargs,
    ) -> str:
        """Enqueue a job for execution.

        Args:
            job_type: Type of job to enqueue
            source_name: Name of the source
            job_function: Async function to execute
            file_type: Optional file type for download/ingest jobs
            **kwargs: Additional arguments to pass to job function

        Returns:
            Job ID for tracking

        """
        job_id = str(uuid.uuid4())

        job_info = JobInfo(
            job_id=job_id,
            job_type=job_type,
            source_name=source_name,
            file_type=file_type,
        )

        # Add source_name and file_type to kwargs so they get passed to the function
        kwargs["source_name"] = source_name
        if file_type:
            # For download jobs, the function expects 'download_type' parameter
            if job_type == JobType.DOWNLOAD:
                kwargs["download_type"] = file_type
            else:
                kwargs["file_type"] = file_type

        async with self._lock:
            self._jobs[job_id] = job_info
            await self._queue.put((job_info, job_function, kwargs))

        logger.debug("Enqueued %s job for %s: %s", job_type.value, source_name, job_id)
        return job_id

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued job.

        Args:
            job_id: ID of job to cancel

        Returns:
            True if job was cancelled, False if not found or already running

        """
        async with self._lock:
            if job_id not in self._jobs:
                return False

            job_info = self._jobs[job_id]

            # Can only cancel queued jobs
            if job_info.status != JobStatus.QUEUED:
                return False

            job_info.status = JobStatus.CANCELLED
            job_info.completed_at = datetime.now()

        logger.info("Cancelled job %s", job_id)
        return True

    def get_job_status(self, job_id: str) -> JobInfo | None:
        """Get status of a specific job."""
        return self._jobs.get(job_id)

    def get_queue_status(self) -> dict[str, Any]:
        """Get current queue status.

        Returns:
            Dictionary with queue information

        """
        queued_jobs = [
            job.to_dict()
            for job in self._jobs.values()
            if job.status == JobStatus.QUEUED
        ]

        return {
            "running": self._running,
            "current_job": self._current_job.to_dict() if self._current_job else None,
            "queue_size": len(queued_jobs),
            "queued_jobs": queued_jobs,
            "total_jobs": len(self._jobs),
        }

    def get_all_jobs(self) -> list[dict[str, Any]]:
        """Get all jobs (for debugging/monitoring)."""
        return [job.to_dict() for job in self._jobs.values()]

    async def _worker(self) -> None:
        """Main worker loop that processes jobs one at a time.

        Follows atomic design principles:
        - Single responsibility: processes one job at a time
        - Error isolation: job failures don't affect queue operation
        - Proper cleanup: ensures job status is always updated
        """
        logger.debug("Job queue worker started")

        while self._running:
            try:
                # Wait for next job with timeout to allow graceful shutdown
                try:
                    job_info, job_function, kwargs = await asyncio.wait_for(
                        self._queue.get(), timeout=1.0
                    )
                except TimeoutError:
                    continue

                # Skip cancelled jobs
                if job_info.status == JobStatus.CANCELLED:
                    continue

                # Execute job
                await self._execute_job(job_info, job_function, kwargs)

            except asyncio.CancelledError:
                logger.debug("Job queue worker cancelled")
                break
            except Exception as e:
                logger.exception(f"Unexpected error in job queue worker: {e}")
                # Continue processing other jobs
                continue

        logger.debug("Job queue worker stopped")

    async def _execute_job(
        self, job_info: JobInfo, job_function: Callable, kwargs: dict[str, Any]
    ) -> None:
        """Execute a single job with proper error handling and status tracking.

        Args:
            job_info: Job information
            job_function: Function to execute
            kwargs: Arguments for the function

        """
        async with self._lock:
            self._current_job = job_info
            job_info.status = JobStatus.RUNNING
            job_info.started_at = datetime.now()

        logger.debug(
            "Executing %s job for %s: %s",
            job_info.job_type.value,
            job_info.source_name,
            job_info.job_id,
        )

        try:
            # Execute the job function
            await job_function(**kwargs)

            # Mark as completed
            async with self._lock:
                job_info.status = JobStatus.COMPLETED
                job_info.completed_at = datetime.now()
                self._current_job = None

            logger.debug(
                "Completed %s job for %s: %s",
                job_info.job_type.value,
                job_info.source_name,
                job_info.job_id,
            )

        except Exception as e:
            # Mark as failed
            async with self._lock:
                job_info.status = JobStatus.FAILED
                job_info.completed_at = datetime.now()
                job_info.error_message = str(e)
                self._current_job = None

            logger.exception(
                "Failed %s job for %s: %s",
                job_info.job_type.value,
                job_info.source_name,
                job_info.job_id,
            )


# Global job queue instance
_job_queue: JobQueue | None = None


async def get_job_queue() -> JobQueue:
    """Get the global job queue instance."""
    global _job_queue
    if _job_queue is None:
        _job_queue = JobQueue()
        await _job_queue.start()
    return _job_queue


async def initialize_job_queue() -> None:
    """Initialize the global job queue."""
    await get_job_queue()
    logger.debug("Global job queue initialized")


async def shutdown_job_queue() -> None:
    """Shutdown the global job queue."""
    global _job_queue
    if _job_queue:
        await _job_queue.stop()
        _job_queue = None
    logger.debug("Global job queue shutdown")


# Atomic job wrapper functions


async def enqueue_download_job(
    source_name: str, file_type: Literal["m3u", "epg"], job_function: Callable, **kwargs
) -> str:
    """Enqueue a download job.

    Args:
        source_name: Name of the source
        file_type: Type of file to download
        job_function: Download function to execute
        **kwargs: Additional arguments

    Returns:
        Job ID for tracking

    """
    queue = await get_job_queue()
    return await queue.enqueue_job(
        JobType.DOWNLOAD, source_name, job_function, file_type=file_type, **kwargs
    )


async def enqueue_ingest_job(
    source_name: str, file_type: Literal["m3u", "epg"], job_function: Callable, **kwargs
) -> str:
    """Enqueue an ingest job.

    Args:
        source_name: Name of the source
        file_type: Type of file to ingest
        job_function: Ingest function to execute
        **kwargs: Additional arguments

    Returns:
        Job ID for tracking

    """
    queue = await get_job_queue()
    return await queue.enqueue_job(
        JobType.INGEST, source_name, job_function, file_type=file_type, **kwargs
    )


async def enqueue_refresh_job(
    source_name: str, file_type: Literal["m3u", "epg"], job_function: Callable, **kwargs
) -> str:
    """Enqueue a refresh job (download + ingest).

    Args:
        source_name: Name of the source
        file_type: Type of file to refresh
        job_function: Refresh function to execute
        **kwargs: Additional arguments

    Returns:
        Job ID for tracking

    """
    queue = await get_job_queue()
    return await queue.enqueue_job(
        JobType.REFRESH, source_name, job_function, file_type=file_type, **kwargs
    )


async def enqueue_bulk_download_job(
    source_name: str, job_function: Callable, **kwargs
) -> str:
    """Enqueue a bulk download job.

    Args:
        source_name: Name of the source (or "all" for all sources)
        job_function: Bulk download function to execute
        **kwargs: Additional arguments

    Returns:
        Job ID for tracking

    """
    queue = await get_job_queue()
    return await queue.enqueue_job(
        JobType.BULK_DOWNLOAD, source_name, job_function, **kwargs
    )


async def enqueue_indexing_job(
    source_name: str, job_function: Callable, **kwargs
) -> str:
    """Enqueue an indexing job.

    Args:
        source_name: Name of the source
        job_function: Indexing function to execute
        **kwargs: Additional arguments

    Returns:
        Job ID for tracking

    """
    queue = await get_job_queue()
    return await queue.enqueue_job(
        JobType.INDEXING, source_name, job_function, **kwargs
    )


async def get_queue_status() -> dict[str, Any]:
    """Get current job queue status."""
    queue = await get_job_queue()
    return queue.get_queue_status()


async def get_job_status(job_id: str) -> dict[str, Any] | None:
    """Get status of a specific job."""
    queue = await get_job_queue()
    job_info = queue.get_job_status(job_id)
    return job_info.to_dict() if job_info else None


async def cancel_job(job_id: str) -> bool:
    """Cancel a queued job."""
    queue = await get_job_queue()
    return await queue.cancel_job(job_id)
