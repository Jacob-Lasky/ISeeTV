"""
Async M3U loader for ISeeTV ETL pipeline.
, modular functions for loading M3U channels into database.
"""

import asyncio
import logging
from typing import AsyncGenerator, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import select

from models.models import M3uChannel
from models.db_models import M3uChannelTable
from ingest.m3u_parser import parse_m3u
from ingest.ingest_tasks import update_ingest_item_progress

logger = logging.getLogger(__name__)


class LoadResult:
    """result container for load operations"""

    def __init__(
        self, record_type: str, record_id: str, status: str, message: str = ""
    ):
        self.record_type = record_type
        self.record_id = record_id
        self.status = status  # 'inserted', 'updated', 'skipped', 'error'
        self.message = message

    def __str__(self):
        return f"{self.record_type}[{self.record_id}]: {self.status} - {self.message}"


def _upsert_m3u_channel(session: Session, channel: M3uChannel) -> LoadResult:
    """function to upsert a single M3U channel"""
    try:
        stmt = insert(M3uChannelTable).values(
            source=channel.source,
            tvg_id=channel.tvg_id,
            name=channel.name,
            stream_url=channel.stream_url,
            logo_url=channel.logo_url,
            group=channel.group,
        )

        # On conflict, update all fields except created_at
        stmt = stmt.on_conflict_do_update(
            index_elements=["source", "tvg_id"],
            set_={
                "name": stmt.excluded.name,
                "stream_url": stmt.excluded.stream_url,
                "logo_url": stmt.excluded.logo_url,
                "group": stmt.excluded.group,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        result = session.execute(stmt)

        # Check if it was an insert or update
        if result.rowcount > 0:
            return LoadResult(
                "M3U_CHANNEL",
                f"{channel.source}:{channel.tvg_id}",
                "upserted",
                f"Channel '{channel.name}' in group '{channel.group}' processed",
            )
        else:
            return LoadResult(
                "M3U_CHANNEL",
                f"{channel.source}:{channel.tvg_id}",
                "skipped",
                "No changes detected",
            )

    except Exception as e:
        logger.error(f"Error upserting M3U channel {channel.tvg_id}: {e}")
        return LoadResult(
            "M3U_CHANNEL", f"{channel.source}:{channel.tvg_id}", "error", str(e)
        )


async def load_m3u_channels_async(
    session: Session,
    file_path: str,
    source_name: str,
    task_id: Optional[str] = None,
    batch_size: int = 200,
) -> AsyncGenerator[LoadResult, None]:
    """Async generator that loads M3U channels and yields results as they're processed"""
    logger.info(
        f"Starting async M3U channel load from {file_path} for source {source_name}"
    )

    try:
        # Parse channels (this is synchronous but usually fast)
        channels = parse_m3u(file_path, source_name)
        logger.info(f"Parsed {len(channels)} M3U channels")

        # Update task progress if task_id provided
        if task_id:
            update_ingest_item_progress(
                task_id, "Loading M3U channels...", 0, "channels"
            )

        # Process in batches to avoid blocking
        completed_count = 0
        for i in range(0, len(channels), batch_size):
            batch = channels[i : i + batch_size]

            for j, channel in enumerate(batch):
                result = _upsert_m3u_channel(session, channel)
                yield result
                completed_count += 1

                # Update progress periodically
                if task_id and completed_count % 50 == 0:
                    update_ingest_item_progress(
                        task_id,
                        f"Processing channel: {channel.name}",
                        completed_count,
                        "channels",
                    )

                # Yield control periodically to avoid blocking
                if j % 25 == 0:
                    await asyncio.sleep(0)

            # Commit batch
            session.commit()
            logger.debug(f"Committed batch {i//batch_size + 1} of M3U channels")

    except Exception as e:
        logger.error(f"Error in async M3U channel loading: {e}")
        session.rollback()
        yield LoadResult("M3U_CHANNEL", "BATCH", "error", str(e))


async def load_m3u_file_async(
    session: Session, file_path: str, source_name: str, task_id: Optional[str] = None
) -> AsyncGenerator[LoadResult, None]:
    """Main async function to load complete M3U file"""
    logger.info(f"Starting complete M3U file load: {file_path} for {source_name}")

    # Load all M3U channels
    async for result in load_m3u_channels_async(
        session, file_path, source_name, task_id
    ):
        yield result

    logger.info(f"Completed M3U file load for {source_name}")
