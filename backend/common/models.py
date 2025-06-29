from pydantic import BaseModel
from typing import Optional, Literal, Dict
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class Message(BaseModel):
    message: str


class DownloadTaskResponse(BaseModel):
    """Response model for download operations that includes task ID for progress tracking"""

    message: str
    task_id: str


class DownloadAllTasksResponse(BaseModel):
    """Response model for download all operations that includes multiple task IDs"""

    message: str
    task_ids: list[str]


class FileMetadata(BaseModel):
    """Atomic file metadata for downloadable resources"""

    url: str
    last_refresh_started_timestamp: Optional[str] = ""
    last_size_bytes: Optional[int] = 0  # Fallback size for progress tracking
    last_refresh_status: Optional[Literal["success", "failed", "cancelled"]] = None
    last_refresh_finished_timestamp: Optional[str] = ""


class Source(BaseModel):
    """Source model with file metadata for scalable download tracking"""

    name: str
    number_of_connections: Optional[int]
    refresh_every_hours: Optional[int]
    subscription_expires: Optional[str]
    source_timezone: Optional[str]
    enabled: bool
    file_metadata: Dict[str, FileMetadata] = {}

    def get_file_metadata(
        self, file_type: Literal["m3u", "epg"]
    ) -> Optional[FileMetadata]:
        """Get file metadata for a specific file type"""
        return self.file_metadata.get(file_type)

    def update_file_metadata(
        self,
        file_type: Literal["m3u", "epg"],
        url: str,
        size_bytes: Optional[int] = None,
        status: Literal["success", "failed", "cancelled"] = "success",
        set_start_timestamp: bool = False,
    ) -> None:
        """Update file metadata during or after download operation"""
        if file_type not in self.file_metadata:
            self.file_metadata[file_type] = FileMetadata(url=url)

        metadata = self.file_metadata[file_type]
        metadata.url = url

        timestamp = datetime.now(timezone.utc).isoformat()

        # Set start timestamp only when download begins
        if set_start_timestamp:
            metadata.last_refresh_started_timestamp = timestamp

        # Always set finish timestamp and status when this function is called
        metadata.last_refresh_finished_timestamp = timestamp
        metadata.last_refresh_status = status

        if size_bytes is not None:
            metadata.last_size_bytes = size_bytes


class GlobalSettings(BaseModel):
    user_timezone: str
    program_cache_days: int
    theme: str


class DownloadProgress(BaseModel):
    task_id: str
    status: Literal["pending", "downloading", "completed", "failed", "cancelled"]
    current_item: Optional[str]
    total_items: int
    completed_items: int
    bytes_downloaded: int
    total_bytes: int
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
