import hashlib
import math
import os
import re
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import TypedDict

from app.common.download_helper import ProgressDict
from app.common.download_helper import stream_download
from app.common.logger import Logger
from app.common.utils import generate_channel_id

logger = Logger(
    "ISeeTV-M3UService",
    os.environ.get("VERBOSE", "false"),
    os.environ.get("LOG_LEVEL", "INFO"),
    color="GREEN",
)


class ChannelDict(TypedDict):
    channel_id: str
    name: str
    url: str
    group: str
    logo: str | None
    is_missing: bool
    is_favorite: bool


class M3UService:
    def __init__(self, config: dict[str, Any]) -> None:
        self.update_interval = config.get("m3u_update_interval", 24)
        self.last_updated = config.get(
            "m3u_last_updated", datetime(1970, 1, 1).strftime("%Y-%m-%dT%H:%M:%S.%f")
        )
        self.file = config.get("m3u_file", "")
        self.url = config.get("m3u_url", "")
        self.content_length = config.get("m3u_content_length", 0)

    def calculate_hours_since_update(self) -> float:
        if not self.last_updated:
            return -math.inf
        last_updated = datetime.strptime(self.last_updated, "%Y-%m-%dT%H:%M:%S.%f")
        return (datetime.now() - last_updated).total_seconds() / 3600

    async def download(self, url: str) -> AsyncGenerator[ProgressDict, None]:
        """Download M3U file from URL and save to disk"""
        logger.info(f"Downloading M3U from {url}")

        # Setup paths and save file
        data_dir = os.path.join(Path(__file__).resolve().parents[3], "data")
        m3u_file = os.path.join(data_dir, "m3u_content.txt")
        os.makedirs(data_dir, exist_ok=True)

        try:
            async for progress in stream_download(url, self.content_length, m3u_file):
                yield progress

        except Exception as e:
            logger.error(f"Failed to download M3U: {str(e)}")
            raise

        self.url = url
        self.file = m3u_file
        self.last_updated = datetime.now().isoformat()
        self.content_length = os.path.getsize(m3u_file)

    async def read_and_parse(
        self, file_path: str
    ) -> tuple[list[ChannelDict], set[str]]:
        """Read M3U file from disk and parse into channels"""
        try:
            with open(file_path, encoding="utf-8") as file:
                content = file.read()

            channels = self.parse_m3u(content)

            # Get list of channel_ids from parsed channels
            new_channel_ids = {channel["channel_id"] for channel in channels}
            logger.info(f"Found {len(new_channel_ids)} channels in the M3U")

            # Set is_missing=0 for all channels in the update
            for channel in channels:
                channel["is_missing"] = False

            return channels, new_channel_ids

        except Exception as e:
            logger.error(f"Failed to read and parse M3U: {str(e)}")
            raise

    def _generate_channel_id(self, name: str, logo: str) -> str:
        """Generate a unique channel ID from name and logo"""
        unique_string = f"{name}:{logo}"
        # Create an MD5 hash and take first 12 characters
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]

    def _sanitize_name(self, name: str) -> str:
        """Sanitize name to remove special characters to be used in url"""
        return re.sub(r"[^a-zA-Z0-9]+", "-", name)

    def parse_m3u(self, content: str) -> list[ChannelDict]:
        """Parse M3U content into channel objects"""
        lines = content.split("\n")
        channels: list[ChannelDict] = []
        current_channel: ChannelDict | None = None

        for line in lines:
            line = line.strip()

            if line.startswith("#EXTINF:"):
                # Parse channel info
                info = line[8:].split(",", 1)
                if len(info) == 2:
                    attrs = self._parse_attributes(info[0])
                    name = attrs.get("tvg-name", "")
                    # channel_id = generate_channel_id(attrs.get("tvg-id", None), name)
                    channel_id = attrs.get("tvg-id", None)

                    if channel_id:
                        current_channel = {
                            "channel_id": channel_id,
                            "name": name,
                            "group": attrs.get("group-title", "Uncategorized"),
                            "logo": attrs.get("tvg-logo"),
                            "url": "",  # Will be set when we get the URL line
                            "is_missing": False,
                            "is_favorite": False,
                        }
                    else:
                        logger.warning(f"No channel_id found for channel: {name}")

            elif line.startswith("http"):
                if current_channel:
                    current_channel["url"] = line
                    channels.append(current_channel)
                    current_channel = None

            elif (
                line.startswith("#EXTM3U")
                or line.startswith("#EXT-X-SESSION-DATA")
                or line == ""
            ):
                continue
            else:
                logger.warning(f"Unprocessed line: {line}")

        return channels

    def _parse_attributes(self, attr_string: str) -> dict:
        """Parse EXTINF attributes into a dictionary"""
        attrs = {}
        matches = re.finditer(r'([a-zA-Z-]+)="([^"]*)"', attr_string)
        for match in matches:
            key, value = match.groups()
            attrs[key] = value
        return attrs
