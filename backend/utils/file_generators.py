"""File generation utilities for M3U and EPG formats.
Following atomic design principles with pure functions for file generation.
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any
from xml.dom import minidom

from sqlalchemy import text

from common.db import SessionLocal
from common.log_utils import get_logger

logger = get_logger(__name__)


def apply_unified_channel_filtering(
    m3u_channels: list[dict[str, Any]],
    epg_channels: list[dict[str, Any]],
    programs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply unified filtering across M3U and EPG data to ensure cross-consistency.
    If a channel is blacklisted in either M3U or EPG, it's excluded from both outputs.

    Args:
        m3u_channels: List of M3U channel dictionaries
        epg_channels: List of EPG channel dictionaries
        programs: List of program dictionaries

    Returns:
        Tuple of (filtered_m3u_channels, filtered_epg_channels, filtered_programs)

    """
    logger.info("Applying unified channel filtering...")

    # Step 1: Get channels that passed filtering in M3U
    passed_m3u_channels = filter_passed_channels(m3u_channels)
    m3u_valid_ids = {
        channel.get("tvg_id")
        for channel in passed_m3u_channels
        if channel.get("tvg_id")
    }
    logger.info(
        "M3U channels that passed filtering: %s (valid IDs: %s)",
        len(passed_m3u_channels),
        len(m3u_valid_ids),
    )

    # Step 2: Get channels that passed filtering in EPG
    passed_epg_channels = filter_passed_channels(epg_channels)
    epg_valid_ids = {
        channel.get("channel_id")
        for channel in passed_epg_channels
        if channel.get("channel_id")
    }
    logger.info(
        "EPG channels that passed filtering: %s (valid IDs: %s)",
        len(passed_epg_channels),
        len(epg_valid_ids),
    )

    # Step 3: Find intersection - only IDs that exist in BOTH and passed filtering in BOTH
    unified_valid_ids = m3u_valid_ids.intersection(epg_valid_ids)
    logger.info("Unified valid channel IDs (intersection): %s", len(unified_valid_ids))

    # Step 4: Filter M3U channels to only include unified valid IDs
    final_m3u_channels = [
        channel
        for channel in passed_m3u_channels
        if channel.get("tvg_id") in unified_valid_ids
    ]

    # Step 5: Filter EPG channels to only include unified valid IDs
    final_epg_channels = [
        channel
        for channel in passed_epg_channels
        if channel.get("channel_id") in unified_valid_ids
    ]

    # Step 6: Filter programs to only include those with unified valid channel IDs
    passed_programs = filter_passed_channels(programs)
    final_programs = [
        program
        for program in passed_programs
        if program.get("channel_id") in unified_valid_ids
    ]

    logger.info(
        "Final filtering results: M3U=%s, EPG=%s, Programs=%s",
        len(final_m3u_channels),
        len(final_epg_channels),
        len(final_programs),
    )

    return final_m3u_channels, final_epg_channels, final_programs


def filter_passed_channels(channels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter channels to only include those that passed all rules (empty filter_reasons).

    Args:
        channels: List of channel dictionaries with filter_reasons field

    Returns:
        List of channels that passed all filters

    """
    logger.info("Filtering passed channels...")
    passed_channels = []

    for channel in channels:
        filter_reasons = channel.get("filter_reasons", "[]")

        # Handle both string and list formats
        if isinstance(filter_reasons, str):
            try:
                filter_reasons_list = json.loads(filter_reasons)
            except json.JSONDecodeError:
                # If parsing fails, assume it's not empty
                continue
        else:
            filter_reasons_list = filter_reasons or []

        # Only include channels with empty filter_reasons
        if not filter_reasons_list:
            passed_channels.append(channel)

    return passed_channels


def generate_m3u_content(channels: list[dict[str, Any]]) -> str:
    """Generate M3U playlist content from filtered channel data.

    Args:
        channels: List of channel dictionaries (already filtered)

    Returns:
        M3U playlist content as string

    """
    logger.info("Generating M3U content...")
    lines = ["#EXTM3U"]

    for channel in channels:
        # Build EXTINF line with channel metadata
        extinf_parts = ["#EXTINF:-1"]

        # Add tvg-id if available
        if channel.get("tvg_id"):
            extinf_parts.append(f'tvg-id="{channel["tvg_id"]}"')

        # Add tvg-name (use name field)
        if channel.get("name"):
            extinf_parts.append(f'tvg-name="{channel["name"]}"')

        # Add tvg-logo if available
        if channel.get("logo_url"):
            extinf_parts.append(f'tvg-logo="{channel["logo_url"]}"')

        # Add group-title if available
        if channel.get("group"):
            extinf_parts.append(f'group-title="{channel["group"]}"')

        # Add channel name at the end
        extinf_line = " ".join(extinf_parts)
        if channel.get("name"):
            extinf_line += f",{channel['name']}"

        lines.append(extinf_line)

        # Add stream URL
        if channel.get("stream_url"):
            lines.append(channel["stream_url"])

    return "\n".join(lines)


def generate_epg_content(
    channels: list[dict[str, Any]], programs: list[dict[str, Any]]
) -> str:
    """Generate EPG XML content from filtered channel and program data.

    Args:
        channels: List of EPG channel dictionaries (already filtered)
        programs: List of program dictionaries (already filtered)

    Returns:
        EPG XML content as string

    """
    logger.info("Generating EPG content...")

    # Get set of valid channel IDs from filtered channels
    valid_channel_ids = {
        channel.get("channel_id") for channel in channels if channel.get("channel_id")
    }
    logger.info("Found %s valid channel IDs", len(valid_channel_ids))

    # Filter programs to only include those with valid channel IDs
    filtered_programs = [
        program
        for program in programs
        if program.get("channel_id") in valid_channel_ids
    ]
    logger.info(
        "Filtered programs from %s to %s based on valid channels",
        len(programs),
        len(filtered_programs),
    )

    # Create root TV element
    root = ET.Element("tv")
    root.set("generator-info-name", "IPTV")

    # Add channels
    for channel in channels:
        channel_elem = ET.SubElement(root, "channel")
        channel_elem.set("id", channel.get("channel_id", ""))

        # Add display name
        if channel.get("display_name"):
            display_name_elem = ET.SubElement(channel_elem, "display-name")
            display_name_elem.text = channel["display_name"]

        # Add icon if available
        if channel.get("icon_url"):
            icon_elem = ET.SubElement(channel_elem, "icon")
            icon_elem.set("src", channel["icon_url"])

    # Add programs (only those with valid channel IDs)
    for program in filtered_programs:
        programme_elem = ET.SubElement(root, "programme")

        # Format datetime for EPG (YYYYMMDDHHMMSS +ZZZZ)
        if program.get("start_time"):
            start_time = _format_epg_datetime(program["start_time"])
            programme_elem.set("start", start_time)

        if program.get("end_time"):
            end_time = _format_epg_datetime(program["end_time"])
            programme_elem.set("stop", end_time)

        # Add start_timestamp and stop_timestamp if available
        if program.get("start_time"):
            start_timestamp = _datetime_to_timestamp(program["start_time"])
            programme_elem.set("start_timestamp", str(start_timestamp))

        if program.get("end_time"):
            stop_timestamp = _datetime_to_timestamp(program["end_time"])
            programme_elem.set("stop_timestamp", str(stop_timestamp))

        # Set channel reference
        if program.get("channel_id"):
            programme_elem.set("channel", program["channel_id"])

        # Add title
        if program.get("title"):
            title_elem = ET.SubElement(programme_elem, "title")
            title_elem.text = program["title"]

        # Add description
        desc_elem = ET.SubElement(programme_elem, "desc")
        desc_elem.text = program.get("description", "")

    # Convert to pretty-printed XML string
    xml_str = ET.tostring(root, encoding="unicode")

    # Add XML declaration and DOCTYPE
    xml_declaration = (
        '<?xml version="1.0" encoding="utf-8" ?><!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
    )

    # Pretty print the XML
    try:
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="\t", encoding=None)
        # Remove the first line (XML declaration from minidom) and add our own
        lines = pretty_xml.split("\n")[1:]
        pretty_xml = xml_declaration + "\n".join(lines)
        return pretty_xml
    except Exception:
        # Fallback to non-pretty XML if pretty printing fails
        return xml_declaration + xml_str


def _format_epg_datetime(dt_str: str) -> str:
    """Format datetime string for EPG format (YYYYMMDDHHMMSS +0000).

    Args:
        dt_str: Datetime string in ISO format

    Returns:
        EPG formatted datetime string

    """
    logger.debug("Formatting EPG datetime...")
    try:
        # Parse the datetime string
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"

        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

        # Format as YYYYMMDDHHMMSS +0000
        return dt.strftime("%Y%m%d%H%M%S +0000")
    except Exception:
        # Fallback to current time if parsing fails
        return datetime.utcnow().strftime("%Y%m%d%H%M%S +0000")


def _datetime_to_timestamp(dt_str: str) -> int:
    """Convert datetime string to Unix timestamp.

    Args:
        dt_str: Datetime string in ISO format

    Returns:
        Unix timestamp as integer

    """
    logger.debug("Converting datetime to timestamp...")
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"

        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except Exception:
        # Fallback to current timestamp if parsing fails
        return int(datetime.utcnow().timestamp())


def get_filtered_channels_and_programs(
    source: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Get filtered M3U channels, EPG channels, and programs from database.

    Args:
        source: Optional source filter

    Returns:
        Tuple of (m3u_channels, epg_channels, programs) that passed filters

    """
    logger.info("Getting filtered channels and programs...")
    with SessionLocal() as session:
        # Get M3U channels
        m3u_query = "SELECT * FROM m3u_channels"
        params = {}

        if source:
            m3u_query += " WHERE source = :source"
            params["source"] = source

        m3u_result = session.execute(text(m3u_query), params)
        m3u_channels = [dict(row._mapping) for row in m3u_result]

        # Get EPG channels
        epg_query = "SELECT * FROM epg_channels"
        if source:
            epg_query += " WHERE source = :source"

        epg_result = session.execute(text(epg_query), params)
        epg_channels = [dict(row._mapping) for row in epg_result]

        # Get programs
        programs_query = "SELECT * FROM programs"
        if source:
            programs_query += " WHERE source = :source"

        programs_result = session.execute(text(programs_query), params)
        programs = [dict(row._mapping) for row in programs_result]

        return m3u_channels, epg_channels, programs
