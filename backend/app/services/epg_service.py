import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from ..common.download_helper import stream_download

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
