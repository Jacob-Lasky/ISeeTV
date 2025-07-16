"""
Global job queue system for ISeeTV to ensure single-job execution.

This module provides atomic, modular job queue functionality that ensures
only one job runs at a time across the entire application.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Literal
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from common.utils import log_function

logger = logging.getLogger(__name__)


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


@dataclass
class JobInfo:
    """
    Atomic job information container.
    
    Follows atomic design principles:
    - Single responsibility: contains job metadata only
    - Immutable: job info doesn't change after creation (except status)
    - Modular: can be extended with new fields without breaking existing code
    """
    job_id: str
    job_type: JobType
    source_name: str
    file_type: Optional[Literal["m3u", "epg"]] = None
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job info to dictionary for API responses."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type.value,
            "source_name": self.source_name,
            "file_type": self.file_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "progress": self.progress
        }


class JobQueue:
    """
    Atomic global job queue manager.
    
    Follows atomic design principles:
    - Single responsibility: manages job queue and execution
    - Modular: integrates with existing job functions without modification
    - Scalable: handles unlimited job types and sources
    """
    
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._jobs: Dict[str, JobInfo] = {}
        self._current_job: Optional[JobInfo] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()
        
        log_function("JobQueue initialized")
    
    async def start(self) -> None:
        """Start the job queue worker."""
        if self._running:
            logger.warning("Job queue already running")
            return
            
        log_function("Starting job queue worker")
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
    
    async def stop(self) -> None:
        """Stop the job queue worker."""
        if not self._running:
            return
            
        log_function("Stopping job queue worker")
        self._running = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
    
    async def enqueue_job(
        self,
        job_type: JobType,
        source_name: str,
        job_function: Callable,
        file_type: Optional[Literal["m3u", "epg"]] = None,
        **kwargs
    ) -> str:
        """
        Enqueue a job for execution.
        
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
            file_type=file_type
        )
        
        # Add source_name and file_type to kwargs so they get passed to the function
        kwargs['source_name'] = source_name
        if file_type:
            # For download jobs, the function expects 'download_type' parameter
            if job_type == JobType.DOWNLOAD:
                kwargs['download_type'] = file_type
            else:
                kwargs['file_type'] = file_type
        
        async with self._lock:
            self._jobs[job_id] = job_info
            await self._queue.put((job_info, job_function, kwargs))
        
        log_function(f"Enqueued {job_type.value} job for {source_name}: {job_id}")
        return job_id
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a queued job.
        
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
            
        log_function(f"Cancelled job {job_id}")
        return True
    
    def get_job_status(self, job_id: str) -> Optional[JobInfo]:
        """Get status of a specific job."""
        return self._jobs.get(job_id)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status.
        
        Returns:
            Dictionary with queue information
        """
        queued_jobs = [
            job.to_dict() for job in self._jobs.values() 
            if job.status == JobStatus.QUEUED
        ]
        
        return {
            "running": self._running,
            "current_job": self._current_job.to_dict() if self._current_job else None,
            "queue_size": len(queued_jobs),
            "queued_jobs": queued_jobs,
            "total_jobs": len(self._jobs)
        }
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs (for debugging/monitoring)."""
        return [job.to_dict() for job in self._jobs.values()]
    
    async def _worker(self) -> None:
        """
        Main worker loop that processes jobs one at a time.
        
        Follows atomic design principles:
        - Single responsibility: processes one job at a time
        - Error isolation: job failures don't affect queue operation
        - Proper cleanup: ensures job status is always updated
        """
        log_function("Job queue worker started")
        
        while self._running:
            try:
                # Wait for next job with timeout to allow graceful shutdown
                try:
                    job_info, job_function, kwargs = await asyncio.wait_for(
                        self._queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Skip cancelled jobs
                if job_info.status == JobStatus.CANCELLED:
                    continue
                
                # Execute job
                await self._execute_job(job_info, job_function, kwargs)
                
            except asyncio.CancelledError:
                log_function("Job queue worker cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in job queue worker: {e}")
                # Continue processing other jobs
                continue
        
        log_function("Job queue worker stopped")
    
    async def _execute_job(
        self,
        job_info: JobInfo,
        job_function: Callable,
        kwargs: Dict[str, Any]
    ) -> None:
        """
        Execute a single job with proper error handling and status tracking.
        
        Args:
            job_info: Job information
            job_function: Function to execute
            kwargs: Arguments for the function
        """
        async with self._lock:
            self._current_job = job_info
            job_info.status = JobStatus.RUNNING
            job_info.started_at = datetime.now()
        
        log_function(f"Executing {job_info.job_type.value} job for {job_info.source_name}: {job_info.job_id}")
        
        try:
            # Execute the job function
            await job_function(**kwargs)
            
            # Mark as completed
            async with self._lock:
                job_info.status = JobStatus.COMPLETED
                job_info.completed_at = datetime.now()
                self._current_job = None
            
            log_function(f"Completed {job_info.job_type.value} job for {job_info.source_name}: {job_info.job_id}")
            
        except Exception as e:
            # Mark as failed
            async with self._lock:
                job_info.status = JobStatus.FAILED
                job_info.completed_at = datetime.now()
                job_info.error_message = str(e)
                self._current_job = None
            
            logger.error(f"Failed {job_info.job_type.value} job for {job_info.source_name}: {job_info.job_id} - {e}")


# Global job queue instance
_job_queue: Optional[JobQueue] = None


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
    log_function("Global job queue initialized")


async def shutdown_job_queue() -> None:
    """Shutdown the global job queue."""
    global _job_queue
    if _job_queue:
        await _job_queue.stop()
        _job_queue = None
    log_function("Global job queue shutdown")


# Atomic job wrapper functions


async def enqueue_download_job(
    source_name: str,
    file_type: Literal["m3u", "epg"],
    job_function: Callable,
    **kwargs
) -> str:
    """
    Enqueue a download job.
    
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
        JobType.DOWNLOAD,
        source_name,
        job_function,
        file_type=file_type,
        **kwargs
    )


async def enqueue_ingest_job(
    source_name: str,
    file_type: Literal["m3u", "epg"],
    job_function: Callable,
    **kwargs
) -> str:
    """
    Enqueue an ingest job.
    
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
        JobType.INGEST,
        source_name,
        job_function,
        file_type=file_type,
        **kwargs
    )


async def enqueue_refresh_job(
    source_name: str,
    file_type: Literal["m3u", "epg"],
    job_function: Callable,
    **kwargs
) -> str:
    """
    Enqueue a refresh job (download + ingest).
    
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
        JobType.REFRESH,
        source_name,
        job_function,
        file_type=file_type,
        **kwargs
    )


async def enqueue_bulk_download_job(
    source_name: str,
    job_function: Callable,
    **kwargs
) -> str:
    """
    Enqueue a bulk download job.
    
    Args:
        source_name: Name of the source (or "all" for all sources)
        job_function: Bulk download function to execute
        **kwargs: Additional arguments
        
    Returns:
        Job ID for tracking
    """
    queue = await get_job_queue()
    return await queue.enqueue_job(
        JobType.BULK_DOWNLOAD,
        source_name,
        job_function,
        **kwargs
    )


async def get_queue_status() -> Dict[str, Any]:
    """Get current job queue status."""
    queue = await get_job_queue()
    return queue.get_queue_status()


async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get status of a specific job."""
    queue = await get_job_queue()
    job_info = queue.get_job_status(job_id)
    return job_info.to_dict() if job_info else None


async def cancel_job(job_id: str) -> bool:
    """Cancel a queued job."""
    queue = await get_job_queue()
    return await queue.cancel_job(job_id)
