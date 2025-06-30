"""
SQLAlchemy database models for ISeeTV ETL pipeline.
 table definitions for EpgChannel, M3uChannel, and Program.
"""

from sqlalchemy import Column, String, DateTime, Integer, Index
from sqlalchemy.sql import func
from common.db import Base


class EpgChannelTable(Base):
    """SQLAlchemy table model for EPG channels"""

    __tablename__ = "epg_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False)
    channel_id = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    icon_url = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Composite unique constraint for source + channel_id
    __table_args__ = (
        Index("idx_epg_source_channel", "source", "channel_id", unique=True),
        Index("idx_epg_source", "source"),
    )


class M3uChannelTable(Base):
    """SQLAlchemy table model for M3U channels"""

    __tablename__ = "m3u_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False)
    tvg_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    stream_url = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    group = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Composite unique constraint for source + tvg_id
    __table_args__ = (
        Index("idx_m3u_source_tvg", "source", "tvg_id", unique=True),
        Index("idx_m3u_source", "source"),
        Index("idx_m3u_group", "group"),
    )


class ProgramTable(Base):
    """SQLAlchemy table model for EPG programs"""

    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False)
    program_id = Column(String, nullable=False)
    channel_id = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Composite unique constraint for source + program_id
    __table_args__ = (
        Index("idx_program_source_id", "source", "program_id", unique=True),
        Index("idx_program_source_channel", "source", "channel_id"),
        Index("idx_program_time_range", "start_time", "end_time"),
        Index("idx_program_source", "source"),
    )
