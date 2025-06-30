from enum import unique
from pydantic import BaseModel
from typing import Optional, Literal, Dict
import datetime as dt
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


class TotalRecords(BaseModel):
    channels: Optional[int] = 0
    programs: Optional[int] = 0


class FileMetadata(BaseModel):
    """file metadata for downloadable resources"""

    url: str
    last_refresh_started_timestamp: Optional[str] = ""
    last_size_bytes: Optional[int] = 0  # Fallback size for progress tracking
    last_refresh_status: Optional[Literal["success", "failed", "cancelled"]] = None
    last_refresh_finished_timestamp: Optional[str] = ""
    local_path: Optional[str] = ""
    total_records: Optional[TotalRecords] = None


class GlobalSettings(BaseModel):
    user_timezone: str
    program_cache_days: int
    theme: str


class DownloadProgress(BaseModel):
    task_id: str
    status: Literal["pending", "downloading", "completed", "failed", "cancelled"]
    file_type: Literal["m3u", "epg"]
    current_item: Optional[str]
    total_items: int
    completed_items: int
    bytes_downloaded: int
    total_bytes: int
    error_message: Optional[str]
    started_at: dt.datetime
    completed_at: Optional[dt.datetime]


class IngestProgress(BaseModel):
    task_id: str
    status: Literal["pending", "ingesting", "completed", "failed", "cancelled"]
    file_type: Literal["m3u", "epg"]
    current_item: Optional[str]
    total_items: int
    completed_items: int
    error_message: Optional[str]
    started_at: dt.datetime
    completed_at: Optional[dt.datetime]
    source_name: Optional[str] = None  # Source being processed
    current_phase: Optional[str] = None  # For EPG: "channels" or "programs"
    updated_at: Optional[dt.datetime] = None  # Last update timestamp


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
        local_path: Optional[str] = None,
    ) -> None:
        """Update file metadata during or after download operation"""
        if file_type not in self.file_metadata:
            self.file_metadata[file_type] = FileMetadata(url=url)

        metadata = self.file_metadata[file_type]
        metadata.url = url

        timestamp = dt.datetime.now(dt.timezone.utc).isoformat()

        # Set start timestamp only when download begins
        if set_start_timestamp:
            metadata.last_refresh_started_timestamp = timestamp

        # Always set finish timestamp and status when this function is called
        metadata.last_refresh_finished_timestamp = timestamp
        metadata.last_refresh_status = status

        if size_bytes is not None:
            metadata.last_size_bytes = size_bytes

        if local_path is not None:
            metadata.local_path = local_path


class EpgChannel(BaseModel):
    """Channel model from EPG data"""

    source: str  # where the EPG came from
    channel_id: str
    display_name: str
    icon_url: Optional[str]


class M3uChannel(BaseModel):
    """Channel model from M3U playlist data"""

    source: str  # where the M3U came from
    tvg_id: str
    name: str
    stream_url: str
    logo_url: Optional[str]
    group: Optional[str]


class Channel(BaseModel):
    """Unified channel model combining EPG and M3U data"""

    source_epg: Optional[str]
    source_m3u: Optional[str]
    channel_id: str  # unified key — probably tvg-id / epg id
    name: str
    stream_url: Optional[str]
    icon_url: Optional[str]
    group: Optional[str]


class Program(BaseModel):
    """Program model, from an EPG (only from an EPG)"""

    source: str
    program_id: str
    channel_id: str
    start_time: dt.datetime
    end_time: dt.datetime
    title: Optional[str]
    description: Optional[str]
