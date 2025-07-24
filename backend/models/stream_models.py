"""Stream models for joined view of channels and programs."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class StreamQueryParams(BaseModel):
    """Shared query parameters for streams endpoints following atomic design principles."""
    
    group: Optional[str] = None
    page: int = 1
    page_size: int = 100
    sort_field: str = "name"
    sort_order: str = "asc"
    global_filter: Optional[str] = None
    column_filters: Optional[str] = None
    apply_rules: bool = True
    filter_view: str = "matched"


class StreamChannel(BaseModel):
    """Atomic model representing a joined stream channel with M3U and EPG data."""

    # M3U Channel Data (primary)
    m3u_id: int
    source: str
    tvg_id: str  # This is the canonical channel_id
    name: str
    stream_url: str
    logo_url: str | None
    group: str | None
    stream_mode: str

    # EPG Channel Data (joined)
    epg_id: int | None
    display_name: str | None
    icon_url: str | None

    # Metadata
    created_at: datetime
    updated_at: datetime

    # Program counts (aggregated)
    program_count: int = 0
    next_program_title: str | None = None
    next_program_start: datetime | None = None


class StreamProgram(BaseModel):
    """Atomic model representing a program with channel context."""

    # Program Data
    program_id: int
    source: str
    program_uid: str
    channel_id: str
    start_time: datetime
    end_time: datetime
    title: str | None
    description: str | None

    # Channel Context (joined)
    channel_name: str | None
    channel_display_name: str | None
    channel_group: str | None
    stream_url: str | None
    logo_url: str | None
    icon_url: str | None

    # Metadata
    created_at: datetime
    updated_at: datetime


class StreamsResponse(BaseModel):
    """Response model for streams API endpoint."""

    success: bool
    data: list[StreamChannel]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    filters: dict[str, list[dict[str, Any]]] = {}
    filter_view_counts: dict[str, int] = {}


class StreamProgramsResponse(BaseModel):
    """Response model for stream programs API endpoint."""

    success: bool
    data: list[StreamProgram]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    filters: dict[str, list[dict[str, Any]]] = {}
