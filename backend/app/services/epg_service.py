import aiohttp
import logging
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


class EPGService:
    def __init__(self, config: dict):
        self.update_interval = config.get("epg_update_interval", 24)
        self.last_updated = config.get("epg_last_updated", datetime.now().isoformat())
        self.file = config.get("epg_file", "")

    async def download(self, url: str) -> None:
        """Download EPG XML and save it to file"""
        if not url:
            logger.warning("No EPG URL provided")
            return

        logger.info(f"Downloading EPG from {url}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if not response.ok:
                        raise Exception(f"HTTP {response.status}: {response.reason}")

                    content = await response.text()
                    logger.info(f"Downloaded {len(content)} bytes")

                    # Setup paths
                    data_dir = os.path.join(Path(__file__).resolve().parents[3], "data")
                    epg_file = os.path.join(data_dir, "epg_content.xml")
                    config_file = os.path.join(data_dir, "config.json")

                    # Ensure data directory exists
                    os.makedirs(data_dir, exist_ok=True)
                    logger.info(f"Data directory is at {data_dir}")

                    # Write EPG content to file
                    with open(epg_file, "w", encoding="utf-8") as file:
                        file.write(content)
                    logger.info(f"Wrote EPG content to {epg_file}")

                    # update the epg_service with the new file and last_updated
                    self.file = str(epg_file)
                    self.last_updated = datetime.now().isoformat()
                    self.content_length = len(content)

                    return epg_file

        except Exception as e:
            logger.error(f"Failed to download EPG: {str(e)}")
            raise
