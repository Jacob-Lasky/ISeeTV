"""
Async EPG loader for ISeeTV ETL pipeline.
Atomic, modular functions for loading EPG channels and programs into database.
"""

import asyncio
import logging
from typing import AsyncGenerator, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import select

from models.models import EpgChannel, Program
from models.db_models import EpgChannelTable, ProgramTable
from ingest.epg_parser import parse_epg_for_channels, parse_epg_for_programs

logger = logging.getLogger(__name__)


class LoadResult:
    """Atomic result container for load operations"""
    def __init__(self, record_type: str, record_id: str, status: str, message: str = ""):
        self.record_type = record_type
        self.record_id = record_id
        self.status = status  # 'inserted', 'updated', 'skipped', 'error'
        self.message = message

    def __str__(self):
        return f"{self.record_type}[{self.record_id}]: {self.status} - {self.message}"


def _upsert_epg_channel(session: Session, channel: EpgChannel) -> LoadResult:
    """Atomic function to upsert a single EPG channel"""
    try:
        stmt = insert(EpgChannelTable).values(
            source=channel.source,
            channel_id=channel.channel_id,
            display_name=channel.display_name,
            icon_url=channel.icon_url
        )
        
        # On conflict, update all fields except created_at
        stmt = stmt.on_conflict_do_update(
            index_elements=['source', 'channel_id'],
            set_={
                'display_name': stmt.excluded.display_name,
                'icon_url': stmt.excluded.icon_url,
                'updated_at': stmt.excluded.updated_at
            }
        )
        
        result = session.execute(stmt)
        
        # Check if it was an insert or update
        if result.rowcount > 0:
            return LoadResult(
                "EPG_CHANNEL", 
                f"{channel.source}:{channel.channel_id}", 
                "upserted",
                f"Channel '{channel.display_name}' processed"
            )
        else:
            return LoadResult(
                "EPG_CHANNEL", 
                f"{channel.source}:{channel.channel_id}", 
                "skipped",
                "No changes detected"
            )
            
    except Exception as e:
        logger.error(f"Error upserting EPG channel {channel.channel_id}: {e}")
        return LoadResult(
            "EPG_CHANNEL", 
            f"{channel.source}:{channel.channel_id}", 
            "error",
            str(e)
        )


def _upsert_program(session: Session, program: Program) -> LoadResult:
    """Atomic function to upsert a single program"""
    try:
        stmt = insert(ProgramTable).values(
            source=program.source,
            program_id=program.program_id,
            channel_id=program.channel_id,
            start_time=program.start_time,
            end_time=program.end_time,
            title=program.title,
            description=program.description
        )
        
        # On conflict, update all fields except created_at
        stmt = stmt.on_conflict_do_update(
            index_elements=['source', 'program_id'],
            set_={
                'channel_id': stmt.excluded.channel_id,
                'start_time': stmt.excluded.start_time,
                'end_time': stmt.excluded.end_time,
                'title': stmt.excluded.title,
                'description': stmt.excluded.description,
                'updated_at': stmt.excluded.updated_at
            }
        )
        
        result = session.execute(stmt)
        
        if result.rowcount > 0:
            return LoadResult(
                "PROGRAM", 
                f"{program.source}:{program.program_id}", 
                "upserted",
                f"Program '{program.title}' on {program.channel_id} processed"
            )
        else:
            return LoadResult(
                "PROGRAM", 
                f"{program.source}:{program.program_id}", 
                "skipped",
                "No changes detected"
            )
            
    except Exception as e:
        logger.error(f"Error upserting program {program.program_id}: {e}")
        return LoadResult(
            "PROGRAM", 
            f"{program.source}:{program.program_id}", 
            "error",
            str(e)
        )


async def load_epg_channels_async(
    session: Session, 
    file_path: str, 
    source_name: str,
    batch_size: int = 100
) -> AsyncGenerator[LoadResult, None]:
    """Async generator that loads EPG channels and yields results as they're processed"""
    logger.info(f"Starting async EPG channel load from {file_path} for source {source_name}")
    
    try:
        # Parse channels (this is synchronous but fast)
        channels = parse_epg_for_channels(file_path, source_name)
        logger.info(f"Parsed {len(channels)} EPG channels")
        
        # Process in batches to avoid blocking
        for i in range(0, len(channels), batch_size):
            batch = channels[i:i + batch_size]
            
            for channel in batch:
                result = _upsert_epg_channel(session, channel)
                yield result
                
                # Yield control periodically to avoid blocking
                if i % 10 == 0:
                    await asyncio.sleep(0)
            
            # Commit batch
            session.commit()
            logger.debug(f"Committed batch {i//batch_size + 1} of EPG channels")
            
    except Exception as e:
        logger.error(f"Error in async EPG channel loading: {e}")
        session.rollback()
        yield LoadResult("EPG_CHANNEL", "BATCH", "error", str(e))


async def load_programs_async(
    session: Session, 
    file_path: str, 
    source_name: str,
    batch_size: int = 500
) -> AsyncGenerator[LoadResult, None]:
    """Async generator that loads programs and yields results as they're processed"""
    logger.info(f"Starting async program load from {file_path} for source {source_name}")
    
    try:
        # Parse programs (this is synchronous but can be large)
        programs = parse_epg_for_programs(file_path, source_name)
        logger.info(f"Parsed {len(programs)} programs")
        
        # Process in batches to avoid blocking
        for i in range(0, len(programs), batch_size):
            batch = programs[i:i + batch_size]
            
            for j, program in enumerate(batch):
                result = _upsert_program(session, program)
                yield result
                
                # Yield control more frequently for large datasets
                if j % 50 == 0:
                    await asyncio.sleep(0)
            
            # Commit batch
            session.commit()
            logger.debug(f"Committed batch {i//batch_size + 1} of programs")
            
    except Exception as e:
        logger.error(f"Error in async program loading: {e}")
        session.rollback()
        yield LoadResult("PROGRAM", "BATCH", "error", str(e))


async def load_epg_file_async(
    session: Session, 
    file_path: str, 
    source_name: str
) -> AsyncGenerator[LoadResult, None]:
    """Main async function to load complete EPG file (channels + programs)"""
    logger.info(f"Starting complete EPG file load: {file_path} for {source_name}")
    
    # Load channels first
    async for result in load_epg_channels_async(session, file_path, source_name):
        yield result
    
    # Then load programs
    async for result in load_programs_async(session, file_path, source_name):
        yield result
    
    logger.info(f"Completed EPG file load for {source_name}")
