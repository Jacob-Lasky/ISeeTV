from pydantic import BaseModel
from typing import Optional, Literal, Dict
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class Message(BaseModel):
    message: str


class FileMetadata(BaseModel):
    """Atomic file metadata for downloadable resources"""

    url: str
    last_refresh: Optional[str] = ""
    last_size_bytes: Optional[int] = 0  # Fallback size for progress tracking


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
    ) -> None:
        """Update file metadata after successful download"""
        if file_type not in self.file_metadata:
            self.file_metadata[file_type] = FileMetadata(url=url)

        metadata = self.file_metadata[file_type]
        metadata.url = url
        metadata.last_refresh = datetime.now(timezone.utc).isoformat()
        if size_bytes is not None:
            metadata.last_size_bytes = size_bytes


class GlobalSettings(BaseModel):
    user_timezone: str
    program_cache_days: int
    theme: str


class DownloadProgress(BaseModel):
    task_id: str
    status: Literal["pending", "downloading", "completed", "failed"]
    current_item: Optional[str]
    total_items: int
    completed_items: int
    bytes_downloaded: int
    total_bytes: int
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
