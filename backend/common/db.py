# common/state.py or common/db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from common.constants import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def init_db():
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized successfully at {DATABASE_URL}")
    