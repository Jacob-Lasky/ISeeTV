import datetime as dt
import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Message(BaseModel):
    message: str


class DownloadTaskResponse(BaseModel):
    """Response model for download operations that includes task ID for progress tracking."""

    message: str
    task_id: str


class DownloadAllTasksResponse(BaseModel):
    """Response model for download all operations that includes multiple task IDs."""

    message: str
    task_ids: list[str]


class TotalRecords(BaseModel):
    channels: int = 0
    programs: int = 0


class FileMetadata(BaseModel):
    """file metadata for downloadable resources."""

    url: str
    last_refresh_started_timestamp: str | None = ""
    last_size_bytes: int | None = 0  # Fallback size for progress tracking
    last_refresh_status: Literal["success", "failed", "cancelled"] | None = None
    last_refresh_finished_timestamp: str | None = ""
    local_path: str | None = ""
    total_records: TotalRecords = Field(default_factory=lambda: TotalRecords(channels=0, programs=0))


class GlobalSettings(BaseModel):
    user_timezone: str
    theme: str


class DownloadProgress(BaseModel):
    task_id: str
    status: Literal["pending", "downloading", "completed", "failed", "cancelled"]
    file_type: Literal["m3u", "epg"]
    current_item: str | None
    total_items: int
    completed_items: int
    bytes_downloaded: int
    total_bytes: int
    error_message: str | None
    started_at: dt.datetime
    completed_at: dt.datetime | None


class IngestProgress(BaseModel):
    task_id: str
    status: Literal["pending", "ingesting", "completed", "failed", "cancelled"]
    file_type: Literal["m3u", "epg"]
    current_item: str | None
    total_items: int
    completed_items: int
    error_message: str | None
    started_at: dt.datetime
    completed_at: dt.datetime | None
    source_name: str | None = None  # Source being processed
    current_phase: str | None = None  # For EPG: "channels" or "programs"
    updated_at: dt.datetime | None = None  # Last update timestamp


class Source(BaseModel):
    """Source model with file metadata for scalable download tracking."""

    name: str
    number_of_connections: int | None
    refresh_every_hours: int | None
    refresh_time: str | None  # HH:MM
    subscription_expires: str | None
    source_timezone: str | None
    enabled: bool
    rule_mode: Literal["whitelist", "blacklist"] = (
        "blacklist"  # Default to blacklist (start with all channels)
    )
    file_metadata: dict[str, FileMetadata] = {}

    def get_file_metadata(
        self, file_type: Literal["m3u", "epg"]
    ) -> FileMetadata | None:
        """Get file metadata for a specific file type."""
        return self.file_metadata.get(file_type)

    def update_file_metadata(
        self,
        file_type: Literal["m3u", "epg"],
        url: str,
        size_bytes: int | None = None,
        status: Literal["success", "failed", "cancelled"] = "success",
        set_start_timestamp: bool = False,
        local_path: str | None = None,
        channels: int | None = None,
        programs: int | None = None,
    ) -> None:
        """Update file metadata during or after download operation."""
        if file_type not in self.file_metadata:
            self.file_metadata[file_type] = FileMetadata(
                url=url, total_records=TotalRecords(channels=0, programs=0)
            )

        metadata = self.file_metadata[file_type]
        metadata.url = url

        timestamp = dt.datetime.now(dt.UTC).isoformat()

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

        # Update total_records if provided
        if channels is not None or programs is not None:
            if metadata.total_records is None:
                metadata.total_records = TotalRecords(channels=0, programs=0)
            if channels is not None:
                metadata.total_records.channels = channels
            if programs is not None:
                metadata.total_records.programs = programs


class EpgChannel(BaseModel):
    """Channel model from EPG data."""

    source: str  # where the EPG came from
    channel_id: str
    display_name: str
    icon_url: str | None
    filter_reasons: str | None = None  # Reason for filtering (blacklist/whitelist)


class M3uChannel(BaseModel):
    """Channel model from M3U playlist data."""

    source: str
    tvg_id: str
    name: str
    stream_url: str
    logo_url: str | None
    group: str | None
    stream_mode: Literal["live", "on_demand"] = "live"
    filter_reasons: str | None = None  # Reason for filtering (blacklist/whitelist)


class Channel(BaseModel):
    """Unified channel model combining EPG and M3U data."""

    source_epg: str | None
    source_m3u: str | None
    channel_id: str  # unified key — probably tvg-id / epg id
    name: str
    stream_url: str | None
    icon_url: str | None
    group: str | None


class Program(BaseModel):
    """Program model, from an EPG (only from an EPG)."""

    source: str
    program_id: str
    channel_id: str
    start_time: dt.datetime
    end_time: dt.datetime
    title: str | None
    description: str | None
    filter_reasons: str | None = None  # Reason for filtering (blacklist/whitelist)


class TableData(BaseModel):
    records: list[dict[str, Any]]
    total: int
    table_name: str
    source_filter: str | None = None


class TableResponse(BaseModel):
    success: bool
    data: TableData
