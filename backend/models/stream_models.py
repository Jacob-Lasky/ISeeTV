"""Stream models for joined view of channels and programs."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class StreamChannel(BaseModel):
    """Atomic model representing a joined stream channel with M3U and EPG data."""
    
    # M3U Channel Data (primary)
    m3u_id: int
    source: str
    tvg_id: str  # This is the canonical channel_id
    name: str
    stream_url: str
    logo_url: Optional[str]
    group: Optional[str]
    
    # EPG Channel Data (joined)
    epg_id: Optional[int]
    display_name: Optional[str]
    icon_url: Optional[str]
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    
    # Program counts (aggregated)
    program_count: int = 0
    next_program_title: Optional[str] = None
    next_program_start: Optional[datetime] = None


class StreamProgram(BaseModel):
    """Atomic model representing a program with channel context."""
    
    # Program Data
    program_id: int
    source: str
    program_uid: str
    channel_id: str
    start_time: datetime
    end_time: datetime
    title: Optional[str]
    description: Optional[str]
    
    # Channel Context (joined)
    channel_name: Optional[str]
    channel_display_name: Optional[str]
    channel_group: Optional[str]
    stream_url: Optional[str]
    logo_url: Optional[str]
    icon_url: Optional[str]
    
    # Metadata
    created_at: datetime
    updated_at: datetime


class StreamsResponse(BaseModel):
    """Response model for streams API endpoint."""
    
    success: bool
    data: List[StreamChannel]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    filters: Dict[str, List[Dict[str, Any]]] = {}


class StreamProgramsResponse(BaseModel):
    """Response model for stream programs API endpoint."""
    
    success: bool
    data: List[StreamProgram]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    filters: Dict[str, List[Dict[str, Any]]] = {}
