"""Job queue callback wrappers for scheduler integration.

This module provides atomic callback functions that integrate the scheduler
with the global job queue system to ensure single-job execution.
"""

import logging
from typing import Literal

from common.utils import log_function
import json
import os
from common.constants import DATA_PATH
from models.models import Source
from download.downloader import background_single_download_task
from common.job_queue import enqueue_refresh_job
from common.task_manager import DownloadTaskManager, IngestTaskManager
from common.utils import create_task_id

logger = logging.getLogger(__name__)


async def refresh_job_callback_wrapper(
    source_name: str, file_type: Literal["m3u", "epg"]
) -> None:
    """Wrapper function to trigger refresh (download + ingest) via job queue.

    This function integrates scheduled refresh jobs with the global job queue
    to ensure only one job runs at a time across the entire system.

    Args:
        source_name: Name of the source
        file_type: Type of file to refresh

    """
    log_function(f"Scheduler triggering refresh job for {source_name} {file_type}")

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
        if not file_metadata or not file_metadata.url:
            raise ValueError(
                f"No {file_type.upper()} URL defined for source '{source_name}'"
            )

        # Create task IDs for both download and ingest
        download_task_id = create_task_id(source_name, file_type, "download")
        ingest_task_id = create_task_id(source_name, file_type, "ingest")

        # Create download task (1 item per task)
        DownloadTaskManager.create_download_task(download_task_id, 1, file_type)

        # Extract total records for ingest progress tracking
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

        # Create ingest task
        IngestTaskManager.create_ingest_task(
            ingest_task_id, file_type, source_name, total_records, total_steps
        )

        # Enqueue refresh job through the global job queue
        job_id = await enqueue_refresh_job(
            source_name=source_name,
            file_type=file_type,
            job_function=_execute_refresh_job,
            download_task_id=download_task_id,
            ingest_task_id=ingest_task_id,
            sources_file=sources_file,
        )

        log_function(
            f"Scheduler refresh job queued for {source_name} {file_type}: {job_id}"
        )

    except Exception as e:
        logger.error(f"Scheduler refresh job failed for {source_name} {file_type}: {e}")
        raise


async def _execute_refresh_job(
    download_task_id: str,
    ingest_task_id: str,
    source_name: str,
    file_type: Literal["m3u", "epg"],
    sources_file: str,
) -> None:
    """Execute the actual refresh job (download + ingest).

    This function is called by the job queue worker to execute the refresh job.

    Args:
        download_task_id: Task ID for download tracking
        ingest_task_id: Task ID for ingest tracking
        source_name: Name of the source
        file_type: Type of file to refresh
        sources_file: Path to sources configuration file

    """
    log_function(f"Executing refresh job for {source_name} {file_type}")

    try:
        # Import here to avoid circular imports
        from main import background_load_task

        download_dir = os.path.join(DATA_PATH, "sources")

        # Step 1: Download the file
        log_function(f"Starting download for {source_name} {file_type}")
        await background_single_download_task(
            download_task_id, source_name, file_type, sources_file, download_dir
        )
        log_function(f"Download completed for {source_name} {file_type}")

        # Step 2: Load sources to get file path
        with open(sources_file) as f:
            sources = [Source(**source) for source in json.load(f)]

        source = next(
            (source for source in sources if source.name == source_name), None
        )
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        file_metadata = source.get_file_metadata(file_type)
        if not file_metadata or not file_metadata.local_path:
            raise ValueError(
                f"No {file_type.upper()} file path found for source '{source_name}'"
            )

        file_path = file_metadata.local_path

        if not os.path.exists(file_path):
            raise ValueError(
                f"Downloaded file '{file_path}' not found for source '{source_name}'"
            )

        # Step 3: Ingest the file
        log_function(f"Starting ingest for {source_name} {file_type}")
        await background_load_task(ingest_task_id, file_type, file_path, source_name)
        log_function(f"Ingest completed for {source_name} {file_type}")

        log_function(
            f"Refresh job completed successfully for {source_name} {file_type}"
        )

    except Exception as e:
        logger.error(f"Refresh job execution failed for {source_name} {file_type}: {e}")
        raise
