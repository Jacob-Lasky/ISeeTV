"""Async M3U loader for ISeeTV ETL pipeline.
, modular functions for loading M3U channels into database.
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional, List
from common.utils import log_function
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert

from models.models import M3uChannel
from models.db_models import M3uChannelTable
from ingest.m3u_parser import parse_m3u
from common.task_manager import IngestTaskManager, TaskManager
from rules.post_load_rules import apply_post_load_rules

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
    """Function to upsert a single M3U channel"""
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


async def _bulk_upsert_m3u_channels(
    session: Session, channels: List[M3uChannel]
) -> List[LoadResult]:
    """Bulk upsert M3U channels using efficient batch operations"""
    if not channels:
        return []

    try:
        # Prepare data for bulk insert
        channel_data = [
            {
                "source": channel.source,
                "tvg_id": channel.tvg_id,
                "name": channel.name,
                "stream_url": channel.stream_url,
                "logo_url": channel.logo_url,
                "group": channel.group,
                "stream_mode": channel.stream_mode,
            }
            for channel in channels
        ]

        # Use bulk insert with ON CONFLICT DO UPDATE
        stmt = insert(M3uChannelTable)
        stmt = stmt.on_conflict_do_update(
            index_elements=["source", "tvg_id"],
            set_={
                "name": stmt.excluded.name,
                "stream_url": stmt.excluded.stream_url,
                "logo_url": stmt.excluded.logo_url,
                "group": stmt.excluded.group,
                "stream_mode": stmt.excluded.stream_mode,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        # Execute bulk operation
        session.execute(stmt, channel_data)
        session.commit()

        # Create success results for all channels
        results = [
            LoadResult(
                "M3U_CHANNEL",
                f"{channel.source}:{channel.tvg_id}",
                "upserted",
                f"Channel '{channel.name}' in group '{channel.group}' processed",
            )
            for channel in channels
        ]

        logger.debug(f"Bulk upserted {len(channels)} M3U channels")
        return results

    except Exception as e:
        logger.error(f"Error in bulk upsert of M3U channels: {e}")
        session.rollback()

        # Return error results for all channels
        return [
            LoadResult(
                "M3U_CHANNEL",
                f"{channel.source}:{channel.tvg_id}",
                "error",
                str(e),
            )
            for channel in channels
        ]


async def load_m3u_channels_async(
    session: Session,
    file_path: str,
    source_name: str,
    task_id: Optional[str] = None,
    batch_size: int = 1000,
) -> AsyncGenerator[LoadResult, None]:
    """Async generator that loads M3U channels using bulk operations for improved performance"""
    log_function(
        f"Starting async M3U channel load from {file_path} for source {source_name}"
    )

    try:
        # Parse channels (this is synchronous but usually fast)
        channels = parse_m3u(file_path, source_name, task_id)
        log_function(f"Parsed {len(channels)} M3U channels")

        # Update task progress if task_id provided
        if task_id:
            # Update total_items with actual parsed count
            TaskManager.update_total_items(task_id, "ingest", len(channels))

            IngestTaskManager.update_item_progress(
                task_id, "Loading M3U channels...", 0
            )

            IngestTaskManager.update_step_progress(task_id, 3, "Loading", 0)

        # Process in batches using bulk operations
        completed_count = 0
        for i in range(0, len(channels), batch_size):
            batch = channels[i : i + batch_size]

            # Use bulk upsert for the entire batch
            batch_results = await _bulk_upsert_m3u_channels(session, batch)

            # Yield results for each item in the batch
            for result in batch_results:
                yield result
                completed_count += 1

                # Update progress periodically
                if task_id and completed_count % 100 == 0:
                    IngestTaskManager.update_item_progress(
                        task_id,
                        f"Loaded {completed_count} M3U channels",
                        completed_count,
                    )

            # Yield control periodically to avoid blocking
            await asyncio.sleep(0)

            logger.debug(
                f"Committed batch {i // batch_size + 1} of M3U channels ({len(batch)} records)"
            )

    except Exception as e:
        logger.error(f"Error in async M3U channel loading: {e}")
        session.rollback()
        yield LoadResult("M3U_CHANNEL", "BATCH", "error", str(e))


async def load_m3u_file_async(
    session: Session, file_path: str, source_name: str, task_id: Optional[str] = None
) -> AsyncGenerator[LoadResult, None]:
    """Main async function to load complete M3U file"""
    log_function(f"Starting complete M3U file load: {file_path} for {source_name}")

    # Load all M3U channels
    async for result in load_m3u_channels_async(
        session, file_path, source_name, task_id
    ):
        yield result

    log_function(f"Completed M3U file load for {source_name}")

    # Apply post-load rules for traceability
    log_function(f"Applying post-load rules to M3U channels for {source_name}")
    try:
        rule_results = apply_post_load_rules("m3u_channels", source_name)
        log_function(
            f"Post-load rules applied: {rule_results['processed']} processed, {rule_results['filtered']} filtered, {rule_results['passed']} passed"
        )

        # Yield a result for rule application
        yield LoadResult(
            "M3U_CHANNEL",
            "RULES",
            "success",
            f"Applied rules: {rule_results['filtered']} filtered, {rule_results['passed']} passed",
        )
    except Exception as e:
        logger.error(f"Error applying post-load rules: {e}")
        yield LoadResult("M3U_CHANNEL", "RULES", "error", str(e))
