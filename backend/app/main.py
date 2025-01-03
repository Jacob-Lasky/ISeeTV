from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app import models, database
from typing import Optional, Dict, Tuple
from pydantic import BaseModel
import logging
import sys
import datetime
from .services.m3u_service import M3UService
from sqlalchemy import func
from fastapi.responses import StreamingResponse
import requests
from .video_helpers import get_video_codec, transcode_video, transcode_audio_only
from .database import get_db, AsyncSessionLocal
import time
import subprocess
import os
import tempfile
import shutil
import time
import signal
from starlette.staticfiles import StaticFiles
from starlette.routing import Mount
import json
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(asctime)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

DATA_DIRECTORY = os.environ.get("DATA_DIRECTORY")
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


# In-memory cache for channel codecs
codec_cache = {}


async def get_codec(guide_id: str, original_url: str):
    # Check cache
    if guide_id in codec_cache:
        return codec_cache[guide_id]
    else:
        # clear the cache
        clear_cache()

    # Fetch and cache codec
    codec = await get_video_codec(original_url)
    logger.info(f"Cached codec for channel {guide_id}: {codec}")
    codec_cache[guide_id] = codec
    return codec


# gpu availability cache
gpu_availability_cache = {}


async def is_gpu_available(guide_id: str):
    if guide_id in gpu_availability_cache:
        return gpu_availability_cache[guide_id]
    else:
        try:
            result = subprocess.run(
                ["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            is_gpu_available = result.returncode == 0
            logger.info(f"GPU availability: {is_gpu_available}")
            gpu_availability_cache[guide_id] = is_gpu_available
            return is_gpu_available
        except FileNotFoundError:
            return False


def clear_cache():
    global codec_cache
    codec_cache = {}
    logger.info("Cleared codec cache")


def save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)
        logger.info(f"Updated config.json")


def check_config_file():
    if not os.path.exists(CONFIG_FILE):
        logger.info("Creating default config.json")
        save_config({})


def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


@app.on_event("startup")
async def startup_event():
    logger.info("ISeeTV backend starting up...")
    check_config_file()
    config = load_config()
    if "m3u_url" in config:
        async with AsyncSessionLocal() as db:
            try:
                await refresh_m3u(config["m3u_url"], db)
                await db.commit()
            except Exception as e:
                await db.rollback()
                raise


@app.post("/m3u/refresh")
async def refresh_m3u(url: str, db: AsyncSession = Depends(get_db)):
    """Download and process M3U file from URL"""
    logger.info(f"Starting M3U refresh from {url}")

    try:
        # Download and parse M3U
        channels = await m3u_service.download_and_parse(url)

        # Clear existing channels using execute
        await db.execute(delete(models.Channel))

        # Save new channels
        db_channels = [models.Channel(**channel) for channel in channels]
        db.add_all(db_channels)
        await db.commit()

        # save the config
        config = load_config()
        config["m3u_url"] = url
        save_config(config)

        logger.info(f"Successfully saved {len(channels)} channels")
        return {"message": f"Saved {len(channels)} channels"}

    except Exception as e:
        logger.error(f"Failed to refresh M3U: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to refresh M3U: {str(e)}")


@app.get("/channels")
async def get_channels(
    skip: int = 0,
    limit: int = 100,
    group: Optional[str] = None,
    search: Optional[str] = None,
    favorites_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
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

        return {"items": channels, "total": total, "skip": skip, "limit": limit}
    except Exception as e:
        logger.error(f"Error getting channels: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/channels/{guide_id}/favorite")
async def toggle_favorite(guide_id: str, db: AsyncSession = Depends(get_db)):
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
        channel.is_favorite = not channel.is_favorite

        # Commit the change
        await db.commit()
        return channel
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update favorite status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update favorite status")


m3u_service = M3UService()


@app.get("/channels/groups")
async def get_channel_groups(db: AsyncSession = Depends(get_db)):
    """Get all groups and their channel counts"""
    logger.info("Getting channel groups")
    try:
        # Use SQLAlchemy to get groups and counts
        query = (
            select(
                models.Channel.group,
                func.count(models.Channel.channel_number).label("count"),
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
stream_resources: Dict[str, Tuple[str, subprocess.Popen]] = {}

# Keep track of mounted directories
mounted_directories = {}

# Mount a single static files directory for all segments
SEGMENTS_DIR = "/tmp/iseetv_segments"
# remove existing segments directory
if os.path.exists(SEGMENTS_DIR):
    shutil.rmtree(SEGMENTS_DIR)
os.makedirs(SEGMENTS_DIR, exist_ok=True)
app.mount("/segments", StaticFiles(directory=SEGMENTS_DIR), name="segments")


@app.get("/stream/{guide_id}")
async def stream_channel(guide_id: str, db: AsyncSession = Depends(get_db)):
    # Fetch the channel from the database using async syntax
    result = await db.execute(
        select(models.Channel).where(models.Channel.guide_id == guide_id)
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Construct the m3u8 URL
    original_url = f"{channel.url}.m3u8"

    # Create temp directory for this channel if it doesn't exist
    if guide_id not in stream_resources:
        # Create channel-specific directory inside the segments directory
        channel_dir = os.path.join(SEGMENTS_DIR, guide_id)
        os.makedirs(channel_dir, exist_ok=True)
        logger.info(f"Created channel directory: {channel_dir}")

        # Start FFmpeg process
        process, output_m3u8 = transcode_audio_only(original_url, channel_dir, guide_id)

        # Wait for the .m3u8 manifest to be ready
        timeout = 10
        start_time = time.time()
        manifest_ready = False

        while not manifest_ready and time.time() - start_time < timeout:
            if os.path.exists(output_m3u8):
                # Check if at least one segment exists
                segments = [f for f in os.listdir(channel_dir) if f.endswith(".ts")]
                if segments:
                    manifest_ready = True
                    break
            time.sleep(0.5)

        if not manifest_ready:
            # Clean up if manifest isn't ready
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            if os.path.exists(channel_dir):
                shutil.rmtree(channel_dir)
            raise HTTPException(
                status_code=500,
                detail="Failed to generate HLS manifest and segments.",
            )

        # Only store the resources after we know they're ready
        stream_resources[guide_id] = (channel_dir, process)
        logger.info(
            f"Started FFmpeg process for channel {guide_id} with PID {process.pid}"
        )

        # Only after the new channel is ready, clean up other channels
        for existing_channel in list(stream_resources.keys()):
            if existing_channel != guide_id:
                logger.info(
                    f"Cleaning up existing channel {existing_channel} before switching"
                )
                cleanup_channel_resources(existing_channel)

    channel_dir, _ = stream_resources[guide_id]
    output_m3u8 = os.path.join(channel_dir, "output.m3u8")

    # Verify the file exists before returning
    if not os.path.exists(output_m3u8):
        # If file doesn't exist, clean up and raise error
        cleanup_channel_resources(guide_id)
        raise HTTPException(
            status_code=500,
            detail="M3U8 file not found. Channel may have been cleaned up.",
        )

    return FileResponse(output_m3u8, media_type="application/vnd.apple.mpegurl")


def update_base_url(m3u8_path: str, mount_path: str):
    """Update the base URL in the m3u8 file to match the mount path"""
    if os.path.exists(m3u8_path):
        with open(m3u8_path, "r") as f:
            content = f.read()

        # Update the base URL
        content = content.replace("/segments/", f"{mount_path}/")

        with open(m3u8_path, "w") as f:
            f.write(content)


@app.get("/stream/cleanup")
def cleanup_all_channel_resources():
    """Clean up resources for all channels."""
    for guide_id in list(stream_resources.keys()):
        cleanup_channel_resources(guide_id)
    for guide_id in os.listdir(SEGMENTS_DIR):
        logger.info(f"Cleaning up channel {guide_id}")
        shutil.rmtree(os.path.join(SEGMENTS_DIR, guide_id))
    return {"message": "Cleaned up resources for all channels"}


@app.get("/stream/{guide_id}/cleanup")
def cleanup_channel_resources(guide_id: str):
    """Clean up resources for a specific channel."""
    if guide_id in stream_resources:
        channel_dir, process = stream_resources.pop(guide_id)

        # Terminate the FFmpeg process gracefully
        if process.poll() is None:
            logger.info(f"Terminating FFmpeg process for channel {guide_id}")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(
                    f"FFmpeg process for channel {guide_id} didn't terminate gracefully, killing it"
                )
                process.kill()

        # Remove the channel directory
        if os.path.exists(channel_dir):
            logger.info(f"Removing channel directory: {channel_dir}")
            shutil.rmtree(channel_dir, ignore_errors=True)

        return {"message": f"Cleaned up resources for channel {guide_id}"}

    return {"message": f"No resources found for channel {guide_id}"}


def transcode_audio_only(url: str, channel_dir: str, guide_id: str):
    output_m3u8 = os.path.join(channel_dir, "output.m3u8")
    segment_pattern = os.path.join(channel_dir, "segment%03d.ts")

    process = subprocess.Popen(
        [
            "ffmpeg",
            "-i",
            url,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-b:a",
            "128k",
            "-ac",
            "2",
            "-f",
            "hls",
            "-hls_time",
            "4",
            "-hls_list_size",
            "0",
            "-hls_segment_filename",
            segment_pattern,
            "-hls_base_url",
            f"/segments/{guide_id}/",  # Use the guide_id in the base URL
            output_m3u8,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    return process, output_m3u8


# used by hls.js
@app.get("/hls/{segment_path:path}")
async def get_hls_segment(segment_path: str):
    # Proxy the segment requests to the external HLS server
    segment_url = f"https://medcoreplatplus.xyz:443/hls/{segment_path}"
    logger.debug(f"Fetching HLS segment from {segment_url}")
    response = requests.get(segment_url, stream=True)

    if response.status_code == 200:
        return StreamingResponse(
            response.iter_content(chunk_size=1024), media_type="video/MP2T"
        )
    raise HTTPException(
        status_code=response.status_code, detail="Failed to fetch segment"
    )


@app.on_event("shutdown")
def cleanup_temp_dirs():
    # Clean up all channels and the segments directory
    for guide_id in list(stream_resources.keys()):
        cleanup_channel_resources(guide_id)
    if os.path.exists(SEGMENTS_DIR):
        shutil.rmtree(SEGMENTS_DIR)
