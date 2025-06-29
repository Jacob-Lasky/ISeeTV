import os
import asyncio
import httpx
import json
from datetime import datetime, timezone
import pytz
from typing import List, Optional, Tuple, Literal
from common.models import Source
from common.state import get_download_progress


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
) -> Tuple[bool, int]:
    """Download a single file with real-time progress tracking by bytes"""
    try:
        update_download_progress(task_id, current_item=item_name, status="downloading")

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
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)

                            # Update bytes downloaded (frontend can calculate progress)
                            update_download_progress(
                                task_id, bytes_downloaded=downloaded_size
                            )

                            # Yield control to allow other coroutines to run
                            await asyncio.sleep(0)

        # Return both success status and actual downloaded size
        return True, downloaded_size
    except Exception as e:
        update_download_progress(task_id, error_message=str(e))
        return False, 0


async def download_file(
    source_name: str,
    download_type: Literal["m3u", "epg"],
    sources_file: str,
    download_dir: str,
    task_id: Optional[str] = None,
) -> None:
    """Atomic download function for any file type with optional progress tracking"""
    import json
    from common.models import Source

    # Map download type to file extension
    type_config = {
        "m3u": {"extension": "m3u"},
        "epg": {"extension": "xml"},
    }

    if download_type not in type_config:
        raise ValueError(f"Unsupported download type: {download_type}")

    config = type_config[download_type]

    with open(sources_file, "r") as f:
        sources = [Source(**source) for source in json.load(f)]

    for source in sources:
        if source.name == source_name:
            # Get URL from file metadata
            file_metadata = source.get_file_metadata(download_type)
            if file_metadata and file_metadata.url:
                url = file_metadata.url
                filepath = f"{download_dir}/{source.name}.{config['extension']}"

                if task_id:
                    # Get fallback size from source metadata
                    fallback_size = (
                        file_metadata.last_size_bytes if file_metadata else None
                    )

                    # Use progress tracking for background tasks
                    success, size = await download_file_with_progress(
                        url, filepath, task_id, source_name, fallback_size
                    )
                    # Update source metadata with actual downloaded size
                    if success:
                        source.update_file_metadata(download_type, url, size)

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
    try:
        update_download_progress(task_id, status="downloading")

        for source in sources:
            # Get URL from file metadata
            file_metadata = source.get_file_metadata(download_type)
            if not file_metadata or not file_metadata.url:
                continue

            url = file_metadata.url

            # Create filepath
            extension = ".m3u" if download_type == "m3u" else ".xml"
            filepath = f"{download_dir}/{source.name}{extension}"

            # Get fallback size from source metadata
            fallback_size = file_metadata.last_size_bytes if file_metadata else None

            # Download file with fallback size
            success, actual_size = await download_file_with_progress(
                url, filepath, task_id, source.name, fallback_size
            )

            if success:
                # Update source metadata with actual downloaded size
                source.update_file_metadata(download_type, url, actual_size)
                # Update source last_refresh
                file_metadata.last_refresh = datetime.now(timezone.utc).isoformat()

                download_progress = get_download_progress()
                update_download_progress(
                    task_id,
                    completed_items=download_progress[task_id]["completed_items"] + 1,
                )
            else:
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


async def background_single_download_task(
    task_id: str,
    source_name: str,
    download_type: Literal["m3u", "epg"],
    sources_file: str,
    download_dir: str,
) -> None:
    """Background coroutine for downloading a single source with progress tracking"""
    try:
        update_download_progress(
            task_id, status="downloading", current_item=source_name
        )

        # Call the core download functions with progress tracking
        await download_file(
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
