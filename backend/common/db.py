# common/state.py or common/db.py

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from common.constants import DATABASE_URL
from common.log_utils import get_logger

logger = get_logger(__name__)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def init_db():
    """Initialize database and create all tables"""
    logger.info("Initializing database...")

    # Import table models to ensure they're registered with Base

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully at %s", DATABASE_URL)
    logger.debug("Created tables: epg_channels, m3u_channels, programs")
