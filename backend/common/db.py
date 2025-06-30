# common/state.py or common/db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from common.constants import DATABASE_URL
import logging
from common.utils import log_function

logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def init_db():
    """Initialize database and create all tables"""
    log_function("Initializing database...")

    # Import table models to ensure they're registered with Base
    from models.db_models import EpgChannelTable, M3uChannelTable, ProgramTable

    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized successfully at {DATABASE_URL}")
    logger.info("Created tables: epg_channels, m3u_channels, programs")
