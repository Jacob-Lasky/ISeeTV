# Standard library imports
import asyncio
import datetime
import json
import os
import shutil
import subprocess
from collections.abc import AsyncGenerator
from typing import Any
from typing import Optional

# Third-party imports
from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

# Local imports
from app import models
from app.common.logger import Logger

from .database import AsyncSessionLocal
from .database import get_db
from .services.epg_service import EPGService
from .services.m3u_service import M3UService
from .video_helpers import process_video

logger = Logger(
    name="ISeeTV-Backend",
    verbose=os.environ.get("VERBOSE", "false"),
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    color="YELLOW",
)

DATA_DIRECTORY = os.environ.get("DATA_DIRECTORY", "/app/data")
CONFIG_FILE = os.path.join(DATA_DIRECTORY, "config.json")


app = FastAPI()


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChannelBase(BaseModel):
    id: str
    name: str
    url: str
    group: str
    logo: Optional[str] = None
    is_favorite: bool = False
    last_watched: Optional[datetime.datetime] = None


class ChannelResponse(BaseModel):
    guide_id: str
    name: str
    url: str
    group: str
    logo: Optional[str] = None
    is_favorite: bool = False
    last_watched: Optional[datetime.datetime] = None
    created_at: Optional[datetime.datetime] = None
    is_missing: bool = False

    class Config:
        from_attributes = True


# gpu availability cache
gpu_availability_cache: dict[str, bool] = {}


async def is_gpu_available(guide_id: str) -> bool:
    if guide_id in gpu_availability_cache:
        return gpu_availability_cache[guide_id]
    else:
        try:
            result = subprocess.run(["nvidia-smi"], capture_output=True)
            is_gpu_available = result.returncode == 0
            logger.info(f"GPU availability: {is_gpu_available}")
            gpu_availability_cache[guide_id] = is_gpu_available
            return is_gpu_available
        except FileNotFoundError:
            return False


def save_config(config: dict[str, Any]) -> None:
    # first, sort the keys
    config = {k: v for k, v in sorted(config.items(), key=lambda item: item[0])}
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
        logger.info("Updated config.json")


def check_config_file() -> None:
    # if the config file doesn't exist, create it
    if not os.path.exists(CONFIG_FILE):
        logger.info("Creating default config.json")
        save_config(
            {
                "m3u_url": "",
                "epg_url": "",
                "epg_update_interval": 24,
                "m3u_update_interval": 24,
                "update_on_start": True,
                "theme": "dark",
            }
        )


def load_config() -> dict[str, Any]:
    check_config_file()
    with open(CONFIG_FILE) as f:
        config: dict[str, Any] = json.load(f)
        return config


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("ISeeTV backend starting up...")
    check_config_file()
    config = load_config()
    if "m3u_url" in config:
        async with AsyncSessionLocal() as db:
            try:
                m3u_service = M3UService(config=load_config())
                await refresh_m3u(
                    url=config["m3u_url"],
                    interval=m3u_service.update_interval,
                    force=False,
                    db=db,
                )
                await db.commit()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def redirect_to_docs() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.post("/m3u/refresh")
async def refresh_m3u(
    url: str, interval: int, force: bool = False, db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    logger.info("Checking if M3U needs to be refreshed")
    try:
        m3u_service = M3UService(config=load_config())
        needs_refresh = force or m3u_service.calculate_hours_since_update() >= interval

        logger.debug(f"Needs refresh: {needs_refresh}")

        if needs_refresh:
            logger.info(f"Starting M3U refresh from {url}")

            async def m3u_progress_stream() -> AsyncGenerator[bytes, None]:
                # First download the M3U and get the file path
                async for progress in m3u_service.download(url):
                    yield json.dumps(progress).encode() + b"\n"

                # After download is complete, process the file
                channels, new_guide_ids = await m3u_service.read_and_parse(
                    m3u_service.file
                )

                # Mark channels not in new M3U as missing
                await db.execute(
                    update(models.Channel)
                    .where(models.Channel.guide_id.notin_(new_guide_ids))
                    .values(is_missing=1)
                )

                # Get existing favorites
                result = await db.execute(
                    select(models.Channel.guide_id, models.Channel.is_favorite).where(
                        models.Channel.is_favorite
                    )
                )
                favorites = {row.guide_id: row.is_favorite for row in result}

                # Preserve favorite status in new channel data
                for channel in channels:
                    if channel["guide_id"] in favorites:
                        channel["is_favorite"] = favorites[channel["guide_id"]]

                # Insert or update channels
                for channel in channels:
                    stmt = (
                        insert(models.Channel)
                        .prefix_with("OR REPLACE")
                        .values(**channel)
                    )
                    await db.execute(stmt)

                await db.commit()

                # Save config after processing
                config = load_config()
                config["m3u_url"] = m3u_service.url
                config["m3u_last_updated"] = m3u_service.last_updated
                config["m3u_update_interval"] = m3u_service.update_interval
                config["m3u_file"] = m3u_service.file
                config["m3u_content_length"] = m3u_service.content_length
                save_config(config)

                # Final message after everything is done
                yield json.dumps(
                    {
                        "type": "complete",
                        "message": f"Found {len(new_guide_ids)} new channels in the M3U",
                    }
                ).encode() + b"\n"

            return StreamingResponse(
                m3u_progress_stream(), media_type="text/event-stream"
            )
        else:
            logger.info("M3U does not need to be refreshed")
            # Send completion signal even when no update is needed
            return StreamingResponse(
                iter([json.dumps({"type": "complete"}).encode() + b"\n"]),
                media_type="text/event-stream",
            )

    except Exception as e:
        logger.error(f"Failed to refresh M3U: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to refresh M3U: {str(e)}")


@app.post("/epg/refresh")
async def refresh_epg(
    url: str, interval: int, force: bool = False, db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    logger.info("Checking if EPG needs to be refreshed")
    try:
        epg_service = EPGService(load_config())
        needs_refresh = force or epg_service.calculate_hours_since_update() >= interval

        if needs_refresh:
            logger.info(f"Starting EPG refresh from {url}")

            async def epg_progress_stream() -> AsyncGenerator[bytes, None]:
                # Download EPG
                async for progress in epg_service.download(url):
                    # Check if progress is a tuple or dict
                    if isinstance(progress, tuple):
                        current, total = progress
                        yield json.dumps(
                            {
                                "type": "progress",
                                "current": current,
                                "total": total,
                                "message": "Downloading EPG file...",
                            }
                        ).encode() + b"\n"
                    else:
                        # If it's not a tuple, assume it's already formatted correctly
                        yield json.dumps(progress).encode() + b"\n"

                # Parse and store EPG data
                channels, programs = await epg_service.read_and_parse(epg_service.file)

                # Clear existing EPG data
                logger.info("Clearing existing EPG data")
                yield json.dumps(
                    {
                        "type": "progress",
                        "current": 0,
                        "total": len(programs),
                        "message": "Clearing existing EPG data...",
                    }
                ).encode() + b"\n"

                await db.execute(delete(models.EPGChannel))
                await db.execute(delete(models.Program))

                # Insert new data
                logger.info("Inserting new EPG data")
                yield json.dumps(
                    {
                        "type": "progress",
                        "current": 0,
                        "total": len(programs),
                        "message": "Inserting EPG channels...",
                    }
                ).encode() + b"\n"

                for channel in channels:
                    await db.execute(insert(models.EPGChannel).values(**channel))

                logger.info(f"Inserting {len(programs)} EPG programs")
                for i, program in enumerate(programs, 1):
                    if i % 1000 == 0:  # Update progress every 1000 programs
                        yield json.dumps(
                            {
                                "type": "progress",
                                "current": i,
                                "total": len(programs),
                                "message": f"Inserting program data ({i}/{len(programs)})...",
                            }
                        ).encode() + b"\n"
                    await db.execute(insert(models.Program).values(**program))

                logger.info("Committing changes")
                yield json.dumps(
                    {
                        "type": "progress",
                        "current": len(programs),
                        "total": len(programs),
                        "message": "Finalizing EPG update...",
                    }
                ).encode() + b"\n"

                await db.commit()

                # Update config
                config = load_config()
                config["epg_url"] = epg_service.url
                config["epg_last_updated"] = epg_service.last_updated
                config["epg_update_interval"] = epg_service.update_interval
                config["epg_file"] = epg_service.file
                config["epg_content_length"] = epg_service.content_length
                save_config(config)

                yield json.dumps({"type": "complete"}).encode() + b"\n"

            return StreamingResponse(
                epg_progress_stream(), media_type="text/event-stream"
            )
        else:
            logger.info("EPG does not need to be refreshed")
            return StreamingResponse(
                iter([json.dumps({"type": "complete"}).encode() + b"\n"]),
                media_type="text/event-stream",
            )

    except Exception as e:
        logger.error(f"Failed to refresh EPG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/channels")
async def get_channels(
    skip: int = 0,
    limit: int = 100,
    group: Optional[str] = None,
    search: Optional[str] = None,
    favorites_only: bool = False,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    logger.debug(
        f"Getting channels with skip={skip}, limit={limit}, group={group}, search={search}, favorites_only={favorites_only}"
    )
    try:
        # Build the base query
        query = select(models.Channel)

        # Apply filters
        if group:
            query = query.where(models.Channel.group == group)
        if search:
            query = query.where(models.Channel.name.ilike(f"%{search}%"))
        if favorites_only:
            query = query.where(models.Channel.is_favorite)

        # order by channel name
        query = query.order_by(models.Channel.name)

        # Get total count
        count_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Apply pagination if no group specified
        if not group:
            query = query.offset(skip).limit(limit)

        # Execute the query
        result = await db.execute(query)
        channels = result.scalars().all()

        # Convert SQLAlchemy models to Pydantic models
        channel_responses = [
            ChannelResponse.model_validate(channel) for channel in channels
        ]

        return {
            "items": channel_responses,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Error getting channels: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/channels/{guide_id}/favorite")
async def toggle_favorite(
    guide_id: str, db: AsyncSession = Depends(get_db)
) -> ChannelResponse:
    """Toggle favorite status for a channel"""
    logger.info(f"Toggling favorite status for channel {guide_id}")

    try:
        # Get the channel
        result = await db.execute(
            select(models.Channel).where(models.Channel.guide_id == guide_id)
        )
        channel = result.scalar_one_or_none()

        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

        # Toggle the favorite status
        channel.is_favorite = not channel.is_favorite  # type: ignore[assignment]

        logger.info(
            f"Channel {guide_id} is now {'a favorite' if channel.is_favorite else 'not a favorite'}"
        )

        # Commit the change
        await db.commit()
        return ChannelResponse.model_validate(channel)
    except Exception as e:
        logger.error(f"Failed to update favorite status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update favorite status")


m3u_service = M3UService(config=load_config())


@app.get("/channels/groups")
async def get_channel_groups(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get all groups and their channel counts"""
    logger.info("Getting channel groups")
    try:
        # Use SQLAlchemy to get groups and counts
        query = (
            select(
                models.Channel.group,
                func.count(models.Channel.guide_id).label("count"),
            )
            .group_by(models.Channel.group)
            .order_by(models.Channel.group)
        )

        result = await db.execute(query)
        groups = result.all()

        return [
            {"name": group or "Uncategorized", "count": count}
            for group, count in groups
        ]
    except Exception as e:
        logger.error(f"Error getting channel groups: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Temporary directories for streaming
STREAM_RESOURCES: dict[str, dict[str, Any]] = {}

# Mount a single static files directory for all segments
SEGMENTS_DIR = os.path.join(DATA_DIRECTORY, "segments")
logger.info(f"SEGMENTS_DIR: {SEGMENTS_DIR}")
os.makedirs(SEGMENTS_DIR, exist_ok=True)
app.mount("/segments", StaticFiles(directory=SEGMENTS_DIR), name="segments")


@app.get("/stream/{guide_id}")
async def stream_channel(
    guide_id: str,
    db: AsyncSession = Depends(get_db),
    timeout: int = 30,
) -> FileResponse:
    result = await db.execute(
        select(models.Channel).where(models.Channel.guide_id == guide_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    stream_url = f"{channel.url}.m3u8"
    m3u8_name = "stream.m3u8"
    # Create channel-specific directory
    channel_dir = os.path.join(SEGMENTS_DIR, guide_id)
    os.makedirs(channel_dir, exist_ok=True)

    output_m3u8 = os.path.join(channel_dir, m3u8_name)

    if not os.path.exists(output_m3u8):
        logger.info(f"Created channel directory: {channel_dir}")

        # Start the video processing
        ffmpeg_process, monitor = await process_video(
            stream_url, channel_dir, m3u8_name, guide_id
        )
        STREAM_RESOURCES[guide_id] = {
            "dir": channel_dir,
            "ffmpeg_process": ffmpeg_process,
            "monitor": monitor,
        }
        logger.info(f"Started video processing for channel {guide_id}")

        # Clean up other channels
        for existing_channel in list(STREAM_RESOURCES.keys()):
            if existing_channel != guide_id:
                logger.info(f"Cleaning up existing channel {existing_channel}")
                cleanup_channel_resources(existing_channel)

        # Wait for the manifest to be ready
        # However, if the channel directory is deleted, this indicates that the stream was stopped
        x = 0
        while True:
            logger.info(
                f"Waiting for manifest creation for channel {guide_id}{'.' * ((x%3) + 1)}"
            )
            if not os.path.exists(channel_dir):
                msg = "Channel directory not found, likely the stream was manually stopped"
                logger.info(msg)
                raise HTTPException(
                    status_code=404,
                    detail=msg,
                )
            elif os.path.exists(output_m3u8):
                break
            else:
                await asyncio.sleep(1)
                x += 1
                if x > timeout:
                    raise TimeoutError(
                        f"Manifest creation timedout for channel {guide_id}"
                    )

    return FileResponse(output_m3u8, media_type="application/vnd.apple.mpegurl")


def remove_channel_directory(channel_dir: str) -> None:
    if os.path.exists(channel_dir):
        logger.info(f"Removing channel directory: {channel_dir}")
        shutil.rmtree(channel_dir, ignore_errors=True)
    else:
        logger.warning(f"Channel directory {channel_dir} does not exist")


@app.get("/stream/cleanup")
def cleanup_all_channel_resources() -> dict[str, str]:
    """Clean up resources for all channels."""
    for guide_id in os.listdir(SEGMENTS_DIR):
        cleanup_channel_resources(guide_id)
    return {"message": "Cleaned up resources for all channels"}


@app.get("/stream/{guide_id}/cleanup")
def cleanup_channel_resources(guide_id: str) -> dict[str, str]:
    """Clean up resources for a specific channel."""
    if guide_id in STREAM_RESOURCES:
        logger.info(f"Cleaning up resources for channel {guide_id}")
        channel_dir = STREAM_RESOURCES[guide_id]["dir"]
        monitor = STREAM_RESOURCES[guide_id]["monitor"]

        STREAM_RESOURCES.pop(guide_id)
        # Remove the channel directory
        remove_channel_directory(channel_dir)

        # Stop the ffmpeg process
        monitor.stop()

        return {"message": f"Cleaned up resources for channel {guide_id}"}

    return {"message": f"No resources found for channel {guide_id}"}


@app.get("/segments/{guide_id}/{segment_path:path}")
async def get_hls_segment(guide_id: str, segment_path: str) -> FileResponse:
    file_path = os.path.join(SEGMENTS_DIR, guide_id, segment_path)
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return FileResponse(file_path, media_type="video/MP2T", headers=headers)


@app.post("/settings/save")
async def save_settings(request: Request) -> dict[str, Any]:
    """Save settings to config file"""
    logger.info("Saving settings")
    try:
        data = await request.json()
        logger.debug(f"Saving settings: {data}")
        config = load_config()

        # Update config with new settings
        config["m3u_url"] = data.get("m3uUrl", config.get("m3u_url"))
        config["m3u_update_interval"] = data.get("m3uUpdateInterval", 24)
        config["epg_url"] = data.get("epgUrl", config.get("epg_url"))
        config["epg_update_interval"] = data.get("epgUpdateInterval", 24)
        config["update_on_start"] = data.get("updateOnStart", True)
        config["theme"] = data.get("theme", "light")

        save_config(config)
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Failed to save settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/settings")
async def get_settings() -> dict[str, Any]:
    """Get settings from config file"""
    logger.debug("Getting settings")
    try:
        config = load_config()
        return {
            "m3uUrl": config.get("m3u_url", ""),
            "m3uUpdateInterval": config.get("m3u_update_interval", 24),
            "epgUrl": config.get("epg_url", ""),
            "epgUpdateInterval": config.get("epg_update_interval", 24),
            "updateOnStart": config.get("update_on_start", True),
            "theme": config.get("theme", "dark"),
        }
    except Exception as e:
        logger.error(f"Failed to load settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("shutdown")
def cleanup_temp_dirs() -> None:
    # Clean up all channels and the segments directory
    cleanup_all_channel_resources()
    if os.path.exists(SEGMENTS_DIR):
        shutil.rmtree(SEGMENTS_DIR)
