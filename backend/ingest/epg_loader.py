"""Async EPG loader for ISeeTV ETL pipeline.
, modular functions for loading EPG channels and programs into database.
"""

import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from common.log_utils import get_logger
from common.task_manager import IngestTaskManager, TaskManager
from ingest.epg_parser import parse_epg_for_channels, parse_epg_for_programs
from models.db_models import EpgChannelTable, ProgramTable
from models.models import EpgChannel, Program

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


def _upsert_epg_channel(session: Session, channel: EpgChannel) -> LoadResult:
    """Function to upsert a single EPG channel."""
    logger.debug("Upserting EPG channel %s", channel.channel_id)
    try:
        stmt = insert(EpgChannelTable).values(
            source=channel.source,
            channel_id=channel.channel_id,
            display_name=channel.display_name,
            icon_url=channel.icon_url,
        )

        # On conflict, update all fields except created_at
        stmt = stmt.on_conflict_do_update(
            index_elements=["source", "channel_id"],
            set_={
                "display_name": stmt.excluded.display_name,
                "icon_url": stmt.excluded.icon_url,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        result = session.execute(stmt)

        # Check if it was an insert or update
        if result.rowcount > 0:
            return LoadResult(
                "EPG_CHANNEL",
                f"{channel.source}:{channel.channel_id}",
                "upserted",
                f"Channel '{channel.display_name}' processed",
            )
        return LoadResult(
            "EPG_CHANNEL",
            f"{channel.source}:{channel.channel_id}",
            "skipped",
            "No changes detected",
        )

    except Exception as e:
        logger.exception(f"Error upserting EPG channel {channel.channel_id}: {e}")
        return LoadResult(
            "EPG_CHANNEL", f"{channel.source}:{channel.channel_id}", "error", str(e)
        )


async def _bulk_upsert_epg_channels(
    session: Session, channels: list[EpgChannel]
) -> list[LoadResult]:
    """Bulk upsert EPG channels using efficient batch operations."""
    logger.debug("Bulk upserting %s EPG channels", len(channels))
    if not channels:
        return []

    try:
        # Prepare data for bulk insert
        channel_data = [
            {
                "source": channel.source,
                "channel_id": channel.channel_id,
                "display_name": channel.display_name,
                "icon_url": channel.icon_url,
            }
            for channel in channels
        ]

        # Use bulk insert with ON CONFLICT DO UPDATE
        stmt = insert(EpgChannelTable)
        stmt = stmt.on_conflict_do_update(
            index_elements=["source", "channel_id"],
            set_={
                "display_name": stmt.excluded.display_name,
                "icon_url": stmt.excluded.icon_url,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        # Execute bulk operation
        session.execute(stmt, channel_data)
        session.commit()

        # Create success results for all channels
        results = [
            LoadResult(
                "EPG_CHANNEL",
                f"{channel.source}:{channel.channel_id}",
                "upserted",
                f"Channel '{channel.display_name}' processed",
            )
            for channel in channels
        ]

        logger.debug("Bulk upserted %s EPG channels", len(channels))
        return results

    except Exception as e:
        logger.exception("Error in bulk upsert of EPG channels: %s", e)
        session.rollback()

        # Return error results for all channels
        return [
            LoadResult(
                "EPG_CHANNEL",
                f"{channel.source}:{channel.channel_id}",
                "error",
                str(e),
            )
            for channel in channels
        ]


def _upsert_program(session: Session, program: Program) -> LoadResult:
    """Function to upsert a single program."""
    logger.debug("Upserting program %s", program.program_id)
    try:
        stmt = insert(ProgramTable).values(
            source=program.source,
            program_id=program.program_id,
            channel_id=program.channel_id,
            start_time=program.start_time,
            end_time=program.end_time,
            title=program.title,
            description=program.description,
        )

        # On conflict, update all fields except created_at
        stmt = stmt.on_conflict_do_update(
            index_elements=["source", "program_id"],
            set_={
                "channel_id": stmt.excluded.channel_id,
                "start_time": stmt.excluded.start_time,
                "end_time": stmt.excluded.end_time,
                "title": stmt.excluded.title,
                "description": stmt.excluded.description,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        result = session.execute(stmt)

        if result.rowcount > 0:
            return LoadResult(
                "PROGRAM",
                f"{program.source}:{program.program_id}",
                "upserted",
                f"Program '{program.title}' on {program.channel_id} processed",
            )
        return LoadResult(
            "PROGRAM",
            f"{program.source}:{program.program_id}",
            "skipped",
            "No changes detected",
        )

    except Exception as e:
        logger.exception("Error upserting program %s: %s", program.program_id, e)
        return LoadResult(
            "PROGRAM", f"{program.source}:{program.program_id}", "error", str(e)
        )


async def _bulk_upsert_programs(
    session: Session, programs: list[Program]
) -> list[LoadResult]:
    """Bulk upsert programs using efficient batch operations."""
    logger.debug("Bulk upserting %s programs", len(programs))
    if not programs:
        return []

    try:
        # Prepare data for bulk insert
        program_data = [
            {
                "source": program.source,
                "program_id": program.program_id,
                "channel_id": program.channel_id,
                "start_time": program.start_time,
                "end_time": program.end_time,
                "title": program.title,
                "description": program.description,
            }
            for program in programs
        ]

        # Use bulk insert with ON CONFLICT DO UPDATE
        stmt = insert(ProgramTable)
        stmt = stmt.on_conflict_do_update(
            index_elements=["source", "program_id"],
            set_={
                "channel_id": stmt.excluded.channel_id,
                "start_time": stmt.excluded.start_time,
                "end_time": stmt.excluded.end_time,
                "title": stmt.excluded.title,
                "description": stmt.excluded.description,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        # Execute bulk operation
        result = session.execute(stmt, program_data)
        session.commit()

        # Determine status based on rowcount
        # Note: For bulk operations, rowcount represents total affected rows
        # We cannot determine per-record status, so we use aggregate logic
        if result.rowcount > 0:
            status = "upserted"
            message_template = "Program '{title}' on {channel_id} processed"
        else:
            status = "skipped"
            message_template = "Program '{title}' on {channel_id} - no changes detected"

        # Create results for all programs with determined status
        results = [
            LoadResult(
                "PROGRAM",
                f"{program.source}:{program.program_id}",
                status,
                message_template.format(title=program.title, channel_id=program.channel_id),
            )
            for program in programs
        ]

        logger.debug("Bulk upserted %s programs", len(programs))
        return results

    except Exception as e:
        logger.exception("Error in bulk upsert of programs")
        session.rollback()

        # Return error results for all programs
        return [
            LoadResult(
                "PROGRAM",
                f"{program.source}:{program.program_id}",
                "error",
                str(e),
            )
            for program in programs
        ]


async def load_epg_channels_async(
    session: Session,
    file_path: str,
    source_name: str,
    task_id: str | None = None,
    batch_size: int = 1000,
) -> AsyncGenerator[LoadResult, None]:
    """Async generator that loads EPG channels using bulk operations for improved performance."""
    logger.debug(
        "Starting async EPG channel load from %s for source %s", file_path, source_name
    )

    try:
        # Parse channels (this is synchronous but usually fast)
        channels = parse_epg_for_channels(file_path, source_name, task_id)
        logger.info("Parsed %s EPG channels", len(channels))

        # Update task progress if task_id provided
        if task_id:
            # Update total_items with actual parsed count
            TaskManager.update_total_items(task_id, "ingest", len(channels))

            IngestTaskManager.update_item_progress(
                task_id, "Loading EPG channels...", 0, "channels"
            )

            IngestTaskManager.update_step_progress(
                task_id, 3, "Loading EPG channels", 0
            )

        # Process in batches using bulk operations
        logger.info("Loading channels into table")
        completed_count = 0
        for i in range(0, len(channels), batch_size):
            batch = channels[i : i + batch_size]

            # Use bulk upsert for the entire batch
            batch_results = await _bulk_upsert_epg_channels(session, batch)

            # Yield results for each item in the batch
            for result in batch_results:
                yield result
                completed_count += 1

                # Update progress periodically
                if task_id and completed_count % 100 == 0:
                    IngestTaskManager.update_item_progress(
                        task_id,
                        f"Loaded {completed_count} EPG channels",
                        completed_count,
                        "channels",
                    )

            # Yield control periodically to avoid blocking
            await asyncio.sleep(0)

            logger.debug(
                "Committed batch %s of EPG channels (%s records)",
                i // batch_size + 1,
                len(batch),
            )

    except Exception as e:
        logger.exception("Error in async EPG channel loading")
        session.rollback()
        yield LoadResult("EPG_CHANNEL", "BATCH", "error", str(e))


async def load_programs_async(
    session: Session,
    file_path: str,
    source_name: str,
    source_timezone: str,
    task_id: str | None = None,
    batch_size: int = 2000,
) -> AsyncGenerator[LoadResult, None]:
    """Async generator that loads programs using bulk operations for improved performance."""
    logger.info(
        "Starting async program load from %s for source %s", file_path, source_name
    )

    try:
        # Parse programs (this is synchronous but can be large)
        programs = parse_epg_for_programs(
            file_path, source_name, source_timezone, task_id
        )
        logger.info("Parsed %s programs", len(programs))

        # Update task progress if task_id provided
        if task_id:
            # Update total_items with actual parsed count
            TaskManager.update_total_items(task_id, "ingest", len(programs))

            IngestTaskManager.update_item_progress(
                task_id, "Loading programs...", 0, "programs"
            )

            IngestTaskManager.update_step_progress(task_id, 5, "Loading programs", 0)

        # Process in batches using bulk operations
        logger.info("Loading programs into table")
        completed_count = 0
        for i in range(0, len(programs), batch_size):
            batch = programs[i : i + batch_size]

            # Use bulk upsert for the entire batch
            batch_results = await _bulk_upsert_programs(session, batch)

            # Yield results for each item in the batch
            for result in batch_results:
                yield result
                completed_count += 1

                # Update progress periodically
                if task_id and completed_count % 500 == 0:
                    IngestTaskManager.update_item_progress(
                        task_id,
                        f"Loaded {completed_count} programs",
                        completed_count,
                        "programs",
                    )

            # Yield control periodically to avoid blocking
            await asyncio.sleep(0)

            logger.debug(
                "Committed batch %s of programs (%s records)",
                i // batch_size + 1,
                len(batch),
            )

    except Exception as e:
        logger.exception("Error in async program loading")
        session.rollback()
        yield LoadResult("PROGRAM", "BATCH", "error", str(e))


async def load_epg_file_async(
    session: Session,
    file_path: str,
    source_name: str,
    source_timezone: str,
    task_id: str | None = None,
) -> AsyncGenerator[LoadResult, None]:
    """Main async function to load complete EPG file (channels + programs)."""
    logger.info(
        "Starting complete EPG file load: %s for %s with timezone %s",
        file_path,
        source_name,
        source_timezone,
    )

    # Load channels first
    async for result in load_epg_channels_async(
        session, file_path, source_name, task_id
    ):
        yield result

    # Then load programs
    async for result in load_programs_async(
        session, file_path, source_name, source_timezone, task_id
    ):
        yield result

    logger.info("Completed EPG file load for %s", source_name)
