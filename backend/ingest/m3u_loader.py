"""Async M3U loader for ISeeTV ETL pipeline.
, modular functions for loading M3U channels into database.
"""

import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from common.log_utils import get_logger
from common.task_manager import IngestTaskManager, TaskManager
from ingest.m3u_parser import parse_m3u
from models.db_models import M3uChannelTable
from models.models import M3uChannel
from rules.post_load_rules import apply_post_load_rules

logger = get_logger(__name__)


class LoadResult:
    """result container for load operations."""

    def __init__(
        self, record_type: str, record_id: str, status: str, message: str = ""
    ) -> None:
        self.record_type = record_type
        self.record_id = record_id
        self.status = status  # 'inserted', 'updated', 'skipped', 'error'
        self.message = message

    def __str__(self) -> str:
        return f"{self.record_type}[{self.record_id}]: {self.status} - {self.message}"


async def _bulk_upsert_m3u_channels(
    session: Session, channels: list[M3uChannel]
) -> list[LoadResult]:
    """Bulk upsert M3U channels using efficient batch operations."""
    logger.debug("Bulk upserting %s M3U channels", len(channels))
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

        logger.debug("Bulk upserted %s M3U channels", len(channels))
        return results

    except Exception as e:
        logger.exception("Error in bulk upsert of M3U channels")
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
    task_id: str | None = None,
    batch_size: int = 1000,
) -> AsyncGenerator[LoadResult, None]:
    """Async generator that loads M3U channels using bulk operations for improved performance."""
    logger.info(
        "Starting async M3U channel load from %s for source %s", file_path, source_name
    )

    try:
        # Parse channels (this is synchronous but usually fast)
        channels = parse_m3u(file_path, source_name, task_id)
        logger.debug("Parsed %s M3U channels", len(channels))

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
                "Committed batch %s of M3U channels (%s records)",
                i // batch_size + 1,
                len(batch),
            )

    except Exception as e:
        logger.exception("Error in async M3U channel loading")
        session.rollback()
        yield LoadResult("M3U_CHANNEL", "BATCH", "error", str(e))


async def load_m3u_file_async(
    session: Session, file_path: str, source_name: str, task_id: str | None = None
) -> AsyncGenerator[LoadResult, None]:
    """Main async function to load complete M3U file."""
    logger.debug("Starting complete M3U file load: %s for %s", file_path, source_name)

    # Load all M3U channels
    async for result in load_m3u_channels_async(
        session, file_path, source_name, task_id
    ):
        yield result

    logger.debug("Completed M3U file load for %s", source_name)

    logger.info("Applying post-load rules to M3U channels for %s", source_name)
    try:
        rule_results = apply_post_load_rules("m3u_channels", source_name)

        # Yield a result for rule application
        yield LoadResult(
            "M3U_CHANNEL",
            "RULES",
            "success",
            f"Applied rules: {rule_results['filtered']} filtered, {rule_results['passed']} passed",
        )
    except Exception as e:
        logger.exception("Error applying post-load rules")
        yield LoadResult("M3U_CHANNEL", "RULES", "error", str(e))
