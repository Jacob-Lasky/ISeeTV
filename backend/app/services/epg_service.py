import logging
import sys
import os
from pathlib import Path
from datetime import datetime
import math
from ..common.download_helper import stream_download
from ..common.utils import generate_channel_id
import xml.etree.ElementTree as ET
from typing import Tuple, List, Dict
import re
import hashlib

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(asctime)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


class EPGService:
    def __init__(self, config: dict):
        self.update_interval = config.get("epg_update_interval", 24)
        self.last_updated = config.get(
            "epg_last_updated", datetime(1970, 1, 1).strftime("%Y-%m-%dT%H:%M:%S.%f")
        )
        self.file = config.get("epg_file", "")
        self.url = config.get("epg_url", "")
        self.content_length = config.get("epg_content_length", 0)

    def calculate_hours_since_update(self):
        if not self.last_updated:
            return -math.inf
        last_updated = datetime.strptime(self.last_updated, "%Y-%m-%dT%H:%M:%S.%f")
        return (datetime.now() - last_updated).total_seconds() / 3600

    async def download(self, url: str):
        """Download EPG XML and save to disk"""
        logger.info(f"Downloading EPG from {url}")

        # Setup paths and save file
        data_dir = os.path.join(Path(__file__).resolve().parents[3], "data")
        epg_file = os.path.join(data_dir, "epg_content.xml")
        os.makedirs(data_dir, exist_ok=True)

        try:
            async for progress in stream_download(url, self.content_length, epg_file):
                yield progress

        except Exception as e:
            logger.error(f"Failed to download EPG: {str(e)}")
            raise

        self.url = url
        self.file = epg_file
        self.last_updated = datetime.now().isoformat()
        self.content_length = os.path.getsize(epg_file)

    async def read_and_parse(self, file_path: str) -> Tuple[List[Dict], List[str]]:
        """Parse EPG XML and return channel and program data"""
        logger.info(f"Parsing EPG file: {file_path}")

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            channels = []
            channel_ids = set()

            # Parse channels
            for channel in root.findall(".//channel"):
                channel_id = generate_channel_id(
                    channel.get("id"),
                    channel.find("display-name").text,
                    (
                        channel.find("icon").get("src")
                        if channel.find("icon") is not None
                        else None
                    ),
                )

                if channel_id not in channel_ids:
                    channel_ids.add(channel_id)
                    channels.append(
                        {
                            "channel_id": channel_id,
                            "display_name": channel.find("display-name").text,
                            "icon": (
                                channel.find("icon").get("src")
                                if channel.find("icon") is not None
                                else None
                            ),
                            "is_primary": True,  # First occurrence is primary
                        }
                    )
                else:
                    # Additional display names for same channel
                    channels.append(
                        {
                            "channel_id": channel_id,
                            "display_name": channel.find("display-name").text,
                            "icon": (
                                channel.find("icon").get("src")
                                if channel.find("icon") is not None
                                else None
                            ),
                            "is_primary": False,
                        }
                    )

            # Parse programs
            programs = []
            for program in root.findall(".//programme"):
                programs.append(
                    {
                        "channel_id": program.get("channel"),
                        "start_time": datetime.strptime(
                            program.get("start"), "%Y%m%d%H%M%S %z"
                        ),
                        "end_time": datetime.strptime(
                            program.get("stop"), "%Y%m%d%H%M%S %z"
                        ),
                        "title": (
                            program.find("title").text
                            if program.find("title") is not None
                            else "No Title"
                        ),
                        "description": (
                            program.find("desc").text
                            if program.find("desc") is not None
                            else None
                        ),
                        "category": (
                            program.find("category").text
                            if program.find("category") is not None
                            else None
                        ),
                    }
                )

            return channels, programs

        except Exception as e:
            logger.error(f"Failed to parse EPG file: {str(e)}")
            raise
