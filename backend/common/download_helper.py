import logging
import os
import asyncio
import httpx
import json
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Literal
from common.models import Source
from common.state import get_download_progress, is_task_cancelled, remove_cancelled_task
from common.utils import log_info
from fastapi import HTTPException

logger = logging.getLogger(__name__)


# Atomic download utility functions
def create_download_task(task_id: str, total_items: int) -> None:
    """Create a new download task in progress tracking"""
    download_progress = get_download_progress()
    download_progress[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "current_item": None,
        "total_items": total_items,
        "completed_items": 0,
        "bytes_downloaded": 0,
        "total_bytes": 0,
        "error_message": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }


def update_download_progress(task_id: str, **kwargs) -> None:
    """Update download progress atomically"""
    download_progress = get_download_progress()
    if task_id in download_progress:
        download_progress[task_id].update(kwargs)


async def download_file_with_progress(
    url: str,
    filepath: str,
    task_id: str,
    item_name: str,
    fallback_size: Optional[int] = None,
) -> Tuple[bool, int, str]:
    """Download a single file with real-time progress tracking by bytes"""
    log_info()
    try:
        update_download_progress(task_id, current_item=item_name, status="downloading")

        # validate that the file exists
        if not await validate_url(url):
            raise HTTPException(status_code=500, detail=f"URL is not accessible: {url}")

        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Use httpx for streaming async HTTP request
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                # Get total file size from Content-Length header
                total_size = int(response.headers.get("content-length", 0))

                # Use fallback size if Content-Length is missing or zero
                if total_size == 0 and fallback_size is not None:
                    total_size = fallback_size

                downloaded_size = 0

                # Initialize total_bytes for this download
                update_download_progress(task_id, total_bytes=total_size)

                with open(filepath, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        # Check for cancellation before processing each chunk
                        if is_task_cancelled(task_id):
                            logger.info(f"Download task {task_id} cancelled, stopping download")
                            # Clean up the partial file
                            f.close()
                            if os.path.exists(filepath):
                                os.remove(filepath)
                            # Clean up cancellation state
                            remove_cancelled_task(task_id)
                            update_download_progress(
                                task_id, 
                                status="cancelled", 
                                error_message="Download cancelled by user",
                                completed_at=datetime.now(timezone.utc).isoformat()
                            )
                            return False, 0, "cancelled"
                        
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)

                            # Update bytes downloaded (frontend can calculate progress)
                            update_download_progress(
                                task_id, bytes_downloaded=downloaded_size
                            )

                            # Yield control to allow other coroutines to run
                            await asyncio.sleep(0)

        # Return success status, actual downloaded size, and completion status
        return True, downloaded_size, "success"
    except Exception as e:
        update_download_progress(task_id, error_message=str(e))
        return False, 0, "failed"


async def orchestrate_file_download_from_source(
    source_name: str,
    download_type: Literal["m3u", "epg"],
    sources_file: str,
    download_dir: str,
    task_id: Optional[str] = None,
) -> None:
    """Atomic download function for any file type with optional progress tracking"""
    log_info()
    if download_type == "m3u":
        extension = "m3u"
    elif download_type == "epg":
        extension = "xml"
    else:
        raise ValueError(f"Unsupported download type: {download_type}")

    with open(sources_file, "r") as f:
        sources = [Source(**source) for source in json.load(f)]

    if source_name not in [source.name for source in sources]:
        raise HTTPException(
            status_code=404,
            detail=f"Source '{source_name}' not found in sources file. Expected one of [{', '.join([source.name for source in sources])}]",
        )

    for source in sources:
        if source.name == source_name:
            # If we get here, we found the source
            # confirm that the download type exists
            if download_type not in source.file_metadata:
                raise HTTPException(
                    status_code=404,
                    detail=f"Download type '{download_type}' not found for source '{source_name}'",
                )

            # Get URL from file metadata
            file_metadata = source.get_file_metadata(download_type)
            if file_metadata and file_metadata.url:
                url = file_metadata.url

                filepath = f"{download_dir}/{source.name}.{extension}"

                if task_id:
                    # Set start timestamp when download begins
                    source.update_file_metadata(download_type, url, set_start_timestamp=True)
                    
                    # Get fallback size from source metadata
                    fallback_size = (
                        file_metadata.last_size_bytes if file_metadata else None
                    )

                    # Use progress tracking for background tasks
                    success, size, status = await download_file_with_progress(
                        url, filepath, task_id, source_name, fallback_size
                    )
                    # Update source metadata with actual downloaded size and status
                    source.update_file_metadata(download_type, url, size, status=status)

                    # Save updated sources back to file
                    with open(sources_file, "w") as f:
                        json.dump([s.dict() for s in sources], f, indent=2)
                else:
                    # Simple download for direct API calls
                    os.makedirs(download_dir, exist_ok=True)
                    async with httpx.AsyncClient() as client:
                        response = await client.get(url)
                        response.raise_for_status()
                        with open(filepath, "w") as f:
                            f.write(response.text)
            break


async def background_download_task(
    task_id: str,
    sources: List[Source],
    download_type: Literal["m3u", "epg"],
    sources_file: str,
    download_dir: str,
) -> None:
    """Background coroutine for downloading multiple files"""
    log_info()
    try:
        update_download_progress(task_id, status="downloading")

        for source in sources:
            # Get URL from file metadata
            file_metadata = source.get_file_metadata(download_type)
            if not file_metadata or not file_metadata.url:
                continue

            url = file_metadata.url

            # Set start timestamp when download begins
            source.update_file_metadata(download_type, url, set_start_timestamp=True)

            # Create filepath
            extension = ".m3u" if download_type == "m3u" else ".xml"
            filepath = f"{download_dir}/{source.name}{extension}"

            # Get fallback size from source metadata
            fallback_size = file_metadata.last_size_bytes if file_metadata else None

            # Download file with fallback size
            success, actual_size, status = await download_file_with_progress(
                url, filepath, task_id, source.name, fallback_size
            )

            # Update source metadata with actual downloaded size and status
            source.update_file_metadata(download_type, url, actual_size, status=status)

            if success:
                download_progress = get_download_progress()
                update_download_progress(
                    task_id,
                    completed_items=download_progress[task_id]["completed_items"] + 1,
                )
            else:
                # Mark task as failed if not successful (could be failed or cancelled)
                update_download_progress(task_id, status="failed")
                return

        # Update sources file with refresh times
        with open(sources_file, "w") as f:
            json.dump([source.dict() for source in sources], f, indent=2)

        # Mark as completed
        update_download_progress(
            task_id,
            status="completed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            current_item=None,
        )

    except Exception as e:
        update_download_progress(
            task_id,
            status="failed",
            error_message=str(e),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )


async def validate_url(url: str) -> bool:
    """Validate that the URL is accessible"""
    log_info()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.head(url)
            response.raise_for_status()
        return True
    except Exception:
        try:
            # if the server doesn't support HEAD then fallback to a GET of just the first byte
            headers = {"Range": "bytes=0-0"}
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
            return True
        except Exception:
            return False


async def background_single_download_task(
    task_id: str,
    source_name: str,
    download_type: Literal["m3u", "epg"],
    sources_file: str,
    download_dir: str,
) -> None:
    """Background coroutine for downloading a single source with progress tracking"""
    log_info()
    try:
        update_download_progress(
            task_id, status="downloading", current_item=source_name
        )

        # Call the core download functions with progress tracking
        await orchestrate_file_download_from_source(
            source_name, download_type, sources_file, download_dir, task_id
        )

        # Mark as completed
        update_download_progress(
            task_id,
            status="completed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            current_item=None,
            completed_items=1,
        )

    except Exception as e:
        update_download_progress(
            task_id,
            status="failed",
            error_message=str(e),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
