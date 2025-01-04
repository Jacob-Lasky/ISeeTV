import aiohttp
import logging
from typing import List
from ..models import Channel
import re
import hashlib
import sys
import os
import json
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(asctime)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


class M3UService:
    def __init__(self, config: dict):
        self.update_interval = config.get("m3u_update_interval", 24)
        self.last_updated = config.get(
            "m3u_last_updated", datetime(1970, 1, 1).strftime("%Y-%m-%dT%H:%M:%S.%f")
        )
        self.file = config.get("m3u_file", "")
        self.url = config.get("m3u_url", "")
        self.content_length = config.get("m3u_content_length", 0)

    def calculate_hours_since_update(self):
        last_updated = datetime.strptime(self.last_updated, "%Y-%m-%dT%H:%M:%S.%f")
        return (datetime.now() - last_updated).total_seconds() / 3600

    async def download(self, url: str):
        """Download M3U file from URL and save to disk"""
        logger.info(f"Downloading M3U from {url}")

        try:
            self.url = url
            content = []
            total_bytes = 0
            chunk_count = 0

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if not response.ok:
                        raise Exception(f"HTTP {response.status}: {response.reason}")

                    async for chunk in response.content.iter_chunked(8192):
                        chunk_count += 1
                        content.append(chunk)
                        total_bytes += len(chunk)

                        yield {
                            "type": "progress",
                            "current": total_bytes,
                            "total": self.content_length,
                        }

            logger.info(
                f"Download complete. {chunk_count} chunks, {total_bytes} bytes total"
            )
            content_str = b"".join(content).decode("utf-8")

            # Setup paths and save file
            data_dir = os.path.join(Path(__file__).resolve().parents[3], "data")
            m3u_file = os.path.join(data_dir, "m3u_content.txt")
            os.makedirs(data_dir, exist_ok=True)

            with open(m3u_file, "w", encoding="utf-8") as file:
                file.write(content_str)

            self.file = str(m3u_file)
            self.last_updated = datetime.now().isoformat()
            self.content_length = total_bytes

        except Exception as e:
            logger.error(f"Failed to download M3U: {str(e)}")
            raise

    async def read_and_parse(self, file_path: str) -> List[Channel]:
        """Read M3U file from disk and parse into channels"""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()

            channels = self.parse_m3u(content)

            # Get list of guide_ids from parsed channels
            new_guide_ids = {channel["guide_id"] for channel in channels}
            logger.info(f"Found {len(new_guide_ids)} channels in the M3U")

            # Set is_missing=0 for all channels in the update
            for channel in channels:
                channel["is_missing"] = 0

            return channels, new_guide_ids

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

    def parse_m3u(self, content: str) -> List[Channel]:
        """Parse M3U content into channel objects"""
        lines = content.split("\n")
        channels = []
        current_channel = None

        for line in lines:
            line = line.strip()

            if line.startswith("#EXTINF:"):
                # Parse channel info
                info = line[8:].split(",", 1)
                if len(info) == 2:
                    attrs = self._parse_attributes(info[0])

                    name = attrs.get("tvg-name", "")

                    guide_id = self._sanitize_name(name)
                    if guide_id == "":
                        guide_id = self._generate_channel_id(
                            name, attrs.get("tvg-logo", "")
                        )

                    current_channel = {
                        "guide_id": guide_id,
                        "name": name,
                        "group": attrs.get("group-title", "Uncategorized"),
                        "logo": attrs.get("tvg-logo"),
                    }

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

            if any(
                guide_id in existing_guide_ids["guide_id"]
                for existing_guide_ids in channels
            ):
                logger.debug(f"{guide_id} - already exists, renaming")
                guide_id += self._sanitize_name(attrs.get("tvg-id", ""))
                logger.debug(f"--- New guide_id: {guide_id}")

        return channels

    def _parse_attributes(self, attr_string: str) -> dict:
        """Parse EXTINF attributes into a dictionary"""
        attrs = {}
        matches = re.finditer(r'([a-zA-Z-]+)="([^"]*)"', attr_string)
        for match in matches:
            key, value = match.groups()
            attrs[key] = value
        return attrs
