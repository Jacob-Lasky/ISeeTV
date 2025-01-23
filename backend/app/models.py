from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, ForeignKey
from app.database import Base
import datetime


class Channel(Base):
    __tablename__ = "channels"

    guide_id = Column(String, primary_key=True)
    name = Column(String, index=True)
    url = Column(String)
    group = Column(String, index=True)
    logo = Column(String, nullable=True)
    is_favorite = Column(Boolean, default=False)
    last_watched = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_missing = Column(Boolean, default=False)


class EPGChannel(Base):
    __tablename__ = "epg_channels"

    id = Column(Integer, primary_key=True)
    channel_id = Column(String, ForeignKey("channels.guide_id"))
    display_name = Column(String, nullable=False)
    icon = Column(String)
    is_primary = Column(Boolean, default=False)


class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True)
    channel_id = Column(String, ForeignKey("channels.guide_id"))
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    category = Column(String)
    created_at = Column(DateTime, default=func.now())
