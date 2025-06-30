import os
from typing import List
from models.models import EpgChannel, Program
from lxml import etree
from lxml.etree import _Element
import datetime as dt
import logging
from collections import defaultdict
from common.utils import log_function

# EPG are usually XML-based with a structure similar to:
"""
<?xml version="1.0" encoding="utf-8" ?><!DOCTYPE tv SYSTEM "xmltv.dtd">
<tv generator-info-name="IPTV">
	<channel id="CHANNEL ID 1">
		<display-name>CHANNEL DISPLAY NAME 1</display-name>
		<icon src="https://channel-icon-url-1.png" />
	</channel>
	<channel id="CHANNEL ID 2">
		<display-name>CHANNEL DISPLAY NAME 2</display-name>
		<icon src="https://channel-icon-url-2.png" />
	</channel>
		
	<programme start="20250702070000 +0000" stop="20250702110000 +0000" start_timestamp="1751439600" stop_timestamp="1751454000" channel="CHANNEL ID 1" >
		<title>CHANNEL DISPLAY NAME 1</title>
		<desc>CHANNEL DISPLAY NAME 1</desc>
	</programme>
	<programme start="20250702110000 +0000" stop="20250702150000 +0000" start_timestamp="1751454000" stop_timestamp="1751468400" channel="CHANNEL ID 2" >
		<title>CHANNEL DISPLAY NAME 2</title>
		<desc>CHANNEL DISPLAY NAME 2</desc>
	</programme>
</tv>

As we parse the above XML, we would see something like this:
    tree = ET.parse(epg_file)
    root = tree.getroot()

    len(root) --> 4
    root.tag --> 'tv'
    root.attrib --> {'generator-info-name': 'IPTV'}
    root.text --> None
    root[0].tag --> "channel"
    root[1].tag --> "channel"
    root[2].tag --> "programme"
    root[3].tag --> "programme"

    root[0].attrib --> {'id': 'CHANNEL ID 1'}
    root[0].attrib["id"] --> "CHANNEL ID 1"
    root[0][0].tag --> "display-name"
    root[0][0].attrib --> {}
    root[0][0].text --> "CHANNEL DISPLAY NAME 1"
    root[0][1].tag --> "icon"
    root[0][1].attrib --> {'src': 'https://channel-icon-url-1.png'}
    root[0][1].text --> None
    root[0][1].attrib["src"] --> 'https://channel-icon-url-1.png'

    root[2].attrib --> {'channel': 'CHANNEL ID 1', 'start': '20250702070000 +0000', 'stop': '20250702110000 +0000', 'start_timestamp': '1751439600', 'stop_timestamp': '1751454000'}
    root[2].attrib["channel"] --> 'CHANNEL ID 1'
    root[2].attrib["start"] --> '20250702070000 +0000'
    root[2].attrib["stop"] --> '20250702110000 +0000'
    root[2].attrib["start_timestamp"] --> '1751439600'
    root[2].attrib["stop_timestamp"] --> '1751454000'
    
"""

logger = logging.getLogger(__name__)

# Expected structure definitions - configuration
EXPECTED_ROOT_TAGS = {"channel", "programme"}  # Only these tags allowed under <tv>
EXPECTED_ROOT_ATTRS = {
    "generator-info-name",
    "generator-info-url",
    "source-info-name",
    "source-info-url",
    "source-data-url",
}

# Expected channel structure
EXPECTED_CHANNEL_ATTRS = {"id"}  # Only 'id' attribute expected on <channel>
EXPECTED_CHANNEL_CHILD_TAGS = {"display-name", "icon", "url", "title", "desc"}

# Expected programme structure
EXPECTED_PROGRAMME_ATTRS = {
    "start",
    "stop",
    "start_timestamp",
    "stop_timestamp",
    "channel",
}
EXPECTED_PROGRAMME_CHILD_TAGS = {
    "title",
    "desc",
}


class ValidationResults:
    def __init__(self):
        self.unexpected_root_tags = defaultdict(int)
        self.unexpected_root_attrs = set()
        self.unexpected_channel_tags = defaultdict(int)
        self.unexpected_channel_attrs = defaultdict(set)
        self.unexpected_programme_tags = defaultdict(int)
        self.unexpected_programme_attrs = defaultdict(set)

    def log_results(self, context: str = ""):
        """Log all validation results in a structured format"""
        prefix = f"[{context}] " if context else ""

        if self.unexpected_root_tags:
            logger.warning(f"{prefix}Unhandled root-level tags found:")
            for tag, count in self.unexpected_root_tags.items():
                logger.warning(f"  - <{tag}>: {count} occurrences")

        if self.unexpected_root_attrs:
            logger.warning(
                f"{prefix}Unhandled root attributes found: {sorted(self.unexpected_root_attrs)}"
            )

        if self.unexpected_channel_tags:
            logger.warning(f"{prefix}Unhandled channel child tags found:")
            for tag, count in self.unexpected_channel_tags.items():
                logger.warning(f"  - <{tag}>: {count} occurrences")

        if self.unexpected_channel_attrs:
            logger.warning(f"{prefix}Unhandled channel attributes found:")
            for channel_id, attrs in self.unexpected_channel_attrs.items():
                logger.warning(f"  - Channel '{channel_id}': {sorted(attrs)}")

        if self.unexpected_programme_tags:
            logger.warning(f"{prefix}Unhandled programme child tags found:")
            for tag, count in self.unexpected_programme_tags.items():
                logger.warning(f"  - <{tag}>: {count} occurrences")

        if self.unexpected_programme_attrs:
            logger.warning(f"{prefix}Unhandled programme attributes found:")
            for prog_id, attrs in self.unexpected_programme_attrs.items():
                logger.warning(f"  - Programme '{prog_id}': {sorted(attrs)}")


validation_results = ValidationResults()


def validate_root_element(root_elem: _Element) -> None:
    """function to validate root <tv> element attributes"""
    for attr in root_elem.attrib.keys():
        if attr not in EXPECTED_ROOT_ATTRS:
            validation_results.unexpected_root_attrs.add(attr)


def validate_channel_element(channel_elem: _Element) -> str:
    """function to validate channel element structure and return channel_id"""
    channel_id = channel_elem.attrib.get("id", "Unknown")

    # Validate channel attributes
    for attr in channel_elem.attrib.keys():
        if attr not in EXPECTED_CHANNEL_ATTRS:
            validation_results.unexpected_channel_attrs[channel_id].add(attr)

    # Validate channel child tags
    for child in channel_elem:
        if child.tag not in EXPECTED_CHANNEL_CHILD_TAGS:
            validation_results.unexpected_channel_tags[child.tag] += 1

    return channel_id


def validate_programme_element(programme_elem: _Element) -> str:
    """function to validate programme element structure and return programme_id"""
    programme_id = programme_elem.attrib.get("program-id") or programme_elem.attrib.get(
        "channel", "Unknown"
    )

    # Validate programme attributes
    for attr in programme_elem.attrib.keys():
        if attr not in EXPECTED_PROGRAMME_ATTRS:
            validation_results.unexpected_programme_attrs[programme_id].add(attr)

    # Validate programme child tags
    for child in programme_elem:
        if child.tag not in EXPECTED_PROGRAMME_CHILD_TAGS:
            validation_results.unexpected_programme_tags[child.tag] += 1

    return programme_id


def parse_epg_for_channels(epg_file: str, source: str) -> List[EpgChannel]:
    """parse an EPG file  and return a list of Channel objects."""
    log_function(f"Parsing EPG file for channels: {epg_file}")

    # Parse the entire tree at once
    tree = etree.parse(epg_file)
    root = tree.getroot()

    if root.tag != "tv":
        logger.error(f"Expected root tag 'tv', found '{root.tag}'")
        return []

    # Validate root element
    validate_root_element(root)

    # Validate root-level tags
    for child in root:
        if child.tag not in EXPECTED_ROOT_TAGS:
            validation_results.unexpected_root_tags[child.tag] += 1

    channels = []

    # Process all channel elements
    for channel_elem in root.findall("channel"):
        channel_id = validate_channel_element(channel_elem)

        try:
            channel_name = get_required_text(
                channel_elem, "display-name", context=channel_id
            )
            # Optional fields - use findtext for non-required elements
            channel_url = channel_elem.findtext("url", "").strip()
            icon_elem = channel_elem.find("icon")
            channel_logo = (
                icon_elem.get("src", "").strip() if icon_elem is not None else ""
            )

            channels.append(
                EpgChannel(
                    source=source,
                    channel_id=channel_id,
                    display_name=channel_name,
                    icon_url=channel_logo,
                )
            )
        except ValueError as e:
            logger.warning(f"[parse_channels] Skipping invalid channel: {e}")
        except Exception as e:
            logger.error(f"[parse_channels] Unexpected error parsing channel: {e}")

    # Log validation results
    validation_results.log_results("Channel Parsing")

    return channels


def parse_epg_for_programs(epg_file: str, source: str) -> List[Program]:
    """Parse an EPG file and return a list of Program objects."""
    log_function(f"Parsing EPG file for programs: {epg_file}")

    # Parse the entire tree at once
    tree = etree.parse(epg_file)
    root = tree.getroot()

    if root.tag != "tv":
        logger.error(f"Expected root tag 'tv', found '{root.tag}'")
        return []

    # Validate root element
    validate_root_element(root)

    # Validate root-level tags
    for child in root:
        if child.tag not in EXPECTED_ROOT_TAGS:
            validation_results.unexpected_root_tags[child.tag] += 1

    programs = []

    # Process all programme elements
    for programme_elem in root.findall("programme"):
        programme_id = validate_programme_element(programme_elem)

        try:
            # Required attributes - strict parsing
            channel_id = get_required_attr(
                programme_elem, "channel", context=programme_id
            )
            start_time = get_required_attr(
                programme_elem, "start_timestamp", context=programme_id
            )
            end_time = get_required_attr(
                programme_elem, "stop_timestamp", context=programme_id
            )

            # Required child elements - strict parsing
            title = get_required_text(programme_elem, "title", context=programme_id)

            # Optional child elements
            description = programme_elem.findtext("desc", "").strip()

            # Generate program_id from channel and start time if not provided
            program_id = f"{channel_id}_{start_time}"

            programs.append(
                Program(
                    source=source,
                    program_id=program_id,
                    channel_id=channel_id,
                    start_time=start_time,
                    end_time=end_time,
                    title=title,
                    description=description,
                )
            )
        except ValueError as e:
            logger.warning(f"[parse_programs] Skipping invalid programme: {e}")
        except Exception as e:
            logger.error(f"[parse_programs] Unexpected error parsing programme: {e}")

    # Log validation results
    validation_results.log_results("Programme Parsing")

    return programs


def get_required_text(elem: _Element, tag: str, context: str = "") -> str:
    """Get the text of a required child tag. Raises ValueError if missing or empty."""
    value = elem.findtext(tag)
    if not value or not value.strip():
        line = getattr(elem, "sourceline", "unknown")
        raise ValueError(f"Missing required <{tag}> at line {line}. Context: {context}")
    return value.strip()


def get_required_attr(elem: _Element, attr: str, context: str = "") -> str:
    """Get a required attribute. Raises ValueError if missing or empty."""
    value = elem.attrib.get(attr)
    if not value or not value.strip():
        line = getattr(elem, "sourceline", "unknown")
        raise ValueError(
            f"Missing required attribute '{attr}' at line {line}. Context: {context}"
        )
    return value.strip()
