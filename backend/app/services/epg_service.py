import csv
import math
import os
import xml.etree.ElementTree as ET
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any
from typing import TypedDict

from app.common.download_helper import ProgressDict
from app.common.download_helper import stream_download
from app.common.logger import Logger

logger = Logger(
    "ISeeTV-EPGService",
    os.environ.get("VERBOSE", "false"),
    os.environ.get("LOG_LEVEL", "INFO"),
    color="LIGHT_GREEN",
)

DATA_DIRECTORY = os.environ.get("DATA_DIRECTORY", "/app/data")


class EPGChannelDict(TypedDict):
    channel_id: str
    display_name: str
    icon: str | None
    is_primary: bool
    source: str


class EPGProgramDict(TypedDict):
    channel_id: str
    start_time: datetime
    end_time: datetime
    title: str
    description: str | None
    category: str | None
    source: str


class EPGService:
    def __init__(self, config: dict[str, Any]) -> None:
        self.update_interval = config.get("epg_update_interval", 24)
        self.last_updated = config.get(
            "epg_last_updated", datetime(1970, 1, 1).strftime("%Y-%m-%dT%H:%M:%S.%f")
        )
        self.file = config.get("epg_file", "")
        self.url = config.get("epg_url", "")
        self.content_length = config.get("epg_content_length", 0)

    def calculate_hours_since_update(self) -> float:
        if not self.last_updated:
            return -math.inf
        last_updated = datetime.strptime(self.last_updated, "%Y-%m-%dT%H:%M:%S.%f")
        return (datetime.now() - last_updated).total_seconds() / 3600

    async def download(self, url: str) -> AsyncGenerator[ProgressDict, None]:
        """Download EPG XML and save to disk"""
        logger.info(f"Downloading EPG from {url}")

        # Setup paths and save file
        epg_file = os.path.join(DATA_DIRECTORY, "epg_content.xml")
        os.makedirs(DATA_DIRECTORY, exist_ok=True)

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

    async def read_and_parse(
        self, file_path: str
    ) -> tuple[list[EPGChannelDict], list[EPGProgramDict]]:
        """Parse EPG XML and return channel and program data"""
        logger.info(f"Parsing EPG file: {file_path}")
        source = os.path.basename(file_path)

        parse_failures_file = os.path.join(DATA_DIRECTORY, "epg_parse_failures.csv")
        parse_failure_count = 0
        if os.path.exists(parse_failures_file):
            os.remove(parse_failures_file)
            with open(parse_failures_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "channel_id",
                        "start",
                        "end",
                        "title",
                        "description",
                        "category",
                        "reason",
                    ]
                )

        channel_id_failures_file = os.path.join(
            DATA_DIRECTORY, "epg_channel_id_failures.csv"
        )
        channel_id_failure_count = 0
        if os.path.exists(channel_id_failures_file):
            os.remove(channel_id_failures_file)
            with open(channel_id_failures_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "failed_channel_id",
                        "failed_display_name",
                        "existing_channel_id",
                        "existing_display_name",
                        "reason",
                    ]
                )

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            channels: list[EPGChannelDict] = []
            channel_ids = set()

            # Parse channels
            for channel in root.findall(".//channel"):
                channel_id = channel.get("id", "")
                display_name_elem = channel.find("display-name")
                if display_name_elem is not None and display_name_elem.text:
                    display_name = display_name_elem.text

                    if channel_id not in channel_ids:
                        channel_ids.add(channel_id)
                        icon_elem = channel.find("icon")
                        channels.append(
                            {
                                "channel_id": channel_id,
                                "display_name": display_name,
                                "icon": (
                                    icon_elem.get("src")
                                    if icon_elem is not None
                                    else None
                                ),
                                "is_primary": True,  # First occurrence is primary
                                "source": source,
                            }
                        )
                    else:
                        logger.debug(
                            f"Duplicate channel ID: {channel_id} | Display Name: {display_name}"
                        )
                        existing_channel_id = channel_id  # this doesn't feel right but it's how it is defined
                        existing_display_name = [
                            c["display_name"]
                            for c in channels
                            if c["channel_id"] == channel_id
                        ][0]
                        with open(channel_id_failures_file, "a", newline="") as f:
                            writer = csv.writer(f)
                            writer.writerow(
                                [
                                    channel_id,
                                    display_name,
                                    existing_channel_id,
                                    existing_display_name,
                                    "duplicate",
                                ]
                            )
                        channel_id_failure_count += 1
                else:
                    logger.debug(f"No display name found for channel ID: {channel_id}")
                    with open(channel_id_failures_file, "a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(
                            [channel_id, "", "", "", "missing_display_name"]
                        )
                    parse_failure_count += 1
                    continue

            # Parse programs
            programs: list[EPGProgramDict] = []
            for program in root.findall(".//programme"):
                start_str = program.get("start", "")
                end_str = program.get("stop", "")
                title_elem = program.find("title")
                channel_id = program.get("channel", "")

                # Only process if we have all required fields
                if (
                    start_str
                    and end_str
                    and title_elem is not None
                    and title_elem.text is not None
                    and channel_id
                ):
                    desc_elem = program.find("desc")
                    cat_elem = program.find("category")

                    # Get description and category text, ensuring they're strings or None
                    description = desc_elem.text if desc_elem is not None else None
                    category = cat_elem.text if cat_elem is not None else None

                    try:
                        start_time = datetime.strptime(start_str, "%Y%m%d%H%M%S %z")
                        end_time = datetime.strptime(end_str, "%Y%m%d%H%M%S %z")

                        programs.append(
                            {
                                "channel_id": channel_id,
                                "start_time": start_time,
                                "end_time": end_time,
                                "title": title_elem.text,
                                "description": description,
                                "category": category,
                                "source": source,
                            }
                        )
                    except ValueError as e:
                        logger.debug(f"Failed to parse datetime: {e}")
                        with open(parse_failures_file, "a", newline="") as f:
                            writer = csv.writer(f)
                            writer.writerow(
                                [
                                    channel_id,
                                    start_str,
                                    end_str,
                                    title_elem.text,
                                    description,
                                    category,
                                    "bad_datetime",
                                ]
                            )
                        parse_failure_count += 1
                        continue
                else:
                    logger.debug(f"Missing required fields for program: {program}")
                    with open(parse_failures_file, "a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(
                            [
                                channel_id,
                                start_str,
                                end_str,
                                title_elem.text if title_elem else "",
                                description,
                                category,
                                "missing_fields",
                            ]
                        )
                    parse_failure_count += 1
                    continue

            logger.info(f"Parsed {len(channels)} channels and {len(programs)} programs")
            logger.warning(
                f"- {parse_failure_count} parse failures. See details at: {parse_failures_file}"
            )
            logger.warning(
                f"- {channel_id_failure_count} channel ID failures. See details at: {channel_id_failures_file}"
            )

            return channels, programs

        except Exception as e:
            logger.error(f"Failed to parse EPG file: {str(e)}")
            raise

    async def scheduled_update(self) -> None:
        """Run a scheduled update of EPG content"""
        from app.main import refresh_epg

        try:
            await refresh_epg(url=self.url, interval=self.update_interval, force=True)
        except Exception as e:
            logger.error(f"Scheduled EPG update failed: {e}")
