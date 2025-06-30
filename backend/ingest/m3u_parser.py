from typing import List, Optional
from models.models import M3uChannel
from common.utils import log_function
from collections import defaultdict
import logging
import re
import shlex
from fastapi import HTTPException, status

"""
M3U are usually text-based with a structure similar to:

#EXTM3U
#EXT-X-SESSION-DATA:DATA-ID="com.data.1_0_0"
#EXTINF:-1 tvg-id="Channel1.us" tvg-name="Channel 1" tvg-logo="https://channel1.png" group-title="Group 1",Channel 1
https://url.to.stream/extrainfo
#EXTINF:-1 tvg-id="Channel2.us" tvg-name="Channel 2" tvg-logo="https://channel2.png" group-title="Group 2",Channel 2
https://url.to.stream/extrainfo
#EXTINF:-1 tvg-id="Channel3.us" tvg-name="Channel 3" tvg-logo="https://channel3.png" group-title="Group 1",Channel 3
https://url.to.stream/extrainfo
"""
logger = logging.getLogger(__name__)

# Expected M3U tags (case-insensitive)
EXPECTED_M3U_TAGS = {
    "#EXTM3U",
    "#EXT-X-SESSION-DATA",  # HLS session data tag
    "#EXTINF",
}

# Expected EXTINF attributes/keys
EXPECTED_EXTINF_KEYS = {
    "tvg-id",
    "tvg-name",
    "tvg-logo",
    "group-title",
    "timeshift",  # Time-shifting functionality
}


class M3uValidationResults:
    """Container for M3U validation results and logging"""

    def __init__(self):
        self.unhandled_tags = defaultdict(int)
        self.unhandled_extinf_keys = defaultdict(int)
        self.channels_without_urls = []

    def log_results(self, context: str = ""):
        """Log all validation results"""
        prefix = f"[{context}] " if context else ""

        if self.unhandled_tags:
            logger.warning(f"{prefix}Unhandled M3U tags found:")
            for tag, count in self.unhandled_tags.items():
                logger.warning(f"  - {tag}: {count} occurrences")

        if self.unhandled_extinf_keys:
            logger.warning(f"{prefix}Unhandled EXTINF keys found:")
            for key, count in self.unhandled_extinf_keys.items():
                logger.warning(f"  - {key}: {count} occurrences")

        if self.channels_without_urls:
            logger.warning(f"{prefix}Channels without playlist URLs found:")
            for channel_name in self.channels_without_urls:
                logger.warning(f"  - '{channel_name}'")


# Global validation results tracker
validation_results = M3uValidationResults()


def parse_extinf_line(line: str) -> tuple[dict, str]:
    """Parse an EXTINF line and return attributes dict and channel name"""
    # EXTINF format: #EXTINF:duration attr1="val1" attr2="val2",Channel Name
    # Remove #EXTINF: prefix and split on comma to separate attributes from name
    should_be_empty, line = line.split("#EXTINF:")
    if should_be_empty.strip():
        logger.warning(
            f"Found unexpected text before #EXTINF: {should_be_empty.strip()}"
        )

    # Find the last comma to separate attributes from channel name
    comma_idx = line.rfind(",")
    if comma_idx == -1:
        return {}, line.strip()

    attrs_part = line[:comma_idx]
    channel_name = line[comma_idx + 1 :].strip()

    attrs = {}
    # Use regex to parse attributes, handling both quoted and unquoted values
    # Pattern matches: key="value" or key=value
    attr_pattern = r'(\w[\w-]*?)=(?:"([^"]*)"|([^\s]+))'

    for match in re.finditer(attr_pattern, attrs_part):
        key = match.group(1)
        # Use quoted value if present, otherwise unquoted value
        value = match.group(2) if match.group(2) is not None else match.group(3)
        attrs[key] = value or ""

        if key not in EXPECTED_EXTINF_KEYS:
            validation_results.unhandled_extinf_keys[key] += 1

    return attrs, channel_name


def validate_m3u_channel(
    attrs: dict, channel_name: str, stream_url: Optional[str]
) -> Optional[M3uChannel]:
    """Validate and create M3uChannel from parsed data"""
    # Warn if no stream URL
    if not stream_url or not stream_url.strip():
        validation_results.channels_without_urls.append(channel_name)
        logger.warning(f"Channel '{channel_name}' has no playlist URL")
        return None

    # Extract required and optional fields
    tvg_id = attrs.get("tvg-id", "").strip()
    name = attrs.get("tvg-name", channel_name).strip() or channel_name
    logo_url = attrs.get("tvg-logo", "").strip() or None
    group = attrs.get("group-title", "").strip() or None

    # Use channel name as fallback for tvg-id if not provided
    if not tvg_id:
        tvg_id = channel_name

    return M3uChannel(
        source="m3u",  # Will be overridden by caller with actual source
        tvg_id=tvg_id,
        name=name,
        stream_url=stream_url.strip(),
        logo_url=logo_url,
        group=group,
    )


def parse_m3u(m3u_file: str, source: str = "m3u") -> List[M3uChannel]:
    """Parse an M3U file and return a list of M3uChannel objects"""
    log_function(f"Parsing M3U file: {m3u_file}")

    channels = []
    current_extinf_attrs = None
    current_channel_name = None

    try:
        with open(m3u_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                # Handle M3U tags
                if line.startswith("#"):
                    # Extract tag name (everything before first space or colon)
                    tag_match = re.match(r"^(#[A-Z-]+)", line, re.IGNORECASE)
                    if tag_match:
                        tag = tag_match.group(1).upper()

                        if tag == "#EXTINF":
                            # Parse EXTINF line
                            current_extinf_attrs, current_channel_name = (
                                parse_extinf_line(line)
                            )
                        elif tag not in EXPECTED_M3U_TAGS:
                            # Track unhandled tags
                            validation_results.unhandled_tags[tag] += 1

                # Handle stream URLs (non-comment lines)
                elif line.startswith("http"):
                    if (
                        current_extinf_attrs is not None
                        and current_channel_name is not None
                    ):
                        # Create channel from current EXTINF data
                        channel = validate_m3u_channel(
                            current_extinf_attrs, current_channel_name, line
                        )
                        if channel:
                            # Set the actual source
                            channel.source = source
                            channels.append(channel)

                        # Reset for next channel
                        current_extinf_attrs = None
                        current_channel_name = None
                    else:
                        logger.warning(
                            f"Found stream URL without EXTINF at line {line_num}: {line}"
                        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing M3U file {m3u_file}: {e}",
        )

    # Log validation results
    validation_results.log_results(context=f"parse_m3u")

    log_function(f"Successfully parsed {len(channels)} channels from M3U file")
    return channels
