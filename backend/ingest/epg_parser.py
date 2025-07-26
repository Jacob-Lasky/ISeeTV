import datetime as dt
from collections import defaultdict

from lxml import etree
from lxml.etree import _Element

from common.log_utils import get_logger
from common.task_manager import IngestTaskManager
from models.models import EpgChannel, Program

import pytz

logger = get_logger(__name__)

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
    def __init__(self) -> None:
        self.unexpected_root_tags = defaultdict(int)
        self.unexpected_root_attrs = set()
        self.unexpected_channel_tags = defaultdict(int)
        self.unexpected_channel_attrs = defaultdict(set)
        self.unexpected_programme_tags = defaultdict(int)
        self.unexpected_programme_attrs = defaultdict(set)

    def log_results(self, context: str = "") -> None:
        """Log all validation results in a structured format."""
        prefix = f"[{context}] " if context else ""

        if self.unexpected_root_tags:
            logger.warning("%sUnhandled root-level tags found:", prefix)
            for tag, count in self.unexpected_root_tags.items():
                logger.warning("  - <%s>: %s occurrences", tag, count)

        if self.unexpected_root_attrs:
            logger.warning(
                "%sUnhandled root attributes found: %s",
                prefix,
                sorted(self.unexpected_root_attrs),
            )

        if self.unexpected_channel_tags:
            logger.warning("%sUnhandled channel child tags found:", prefix)
            for tag, count in self.unexpected_channel_tags.items():
                logger.warning("  - <%s>: %s occurrences", tag, count)

        if self.unexpected_channel_attrs:
            logger.warning("%sUnhandled channel attributes found:", prefix)
            for channel_id, attrs in self.unexpected_channel_attrs.items():
                logger.warning("  - Channel '%s': %s", channel_id, sorted(attrs))

        if self.unexpected_programme_tags:
            logger.warning("%sUnhandled programme child tags found:", prefix)
            for tag, count in self.unexpected_programme_tags.items():
                logger.warning("  - <%s>: %s occurrences", tag, count)

        if self.unexpected_programme_attrs:
            logger.warning("%sUnhandled programme attributes found:", prefix)
            for prog_id, attrs in self.unexpected_programme_attrs.items():
                logger.warning("  - Programme '%s': %s", prog_id, sorted(attrs))


# Global validation_results for backward compatibility
validation_results = ValidationResults()


def validate_root_element(root_elem: _Element, validation_results: ValidationResults = None) -> None:
    """Function to validate root <tv> element attributes and child tags."""
    if validation_results is None:
        validation_results = ValidationResults()
    
    logger.debug("Validating root element attributes")
    for attr in root_elem.attrib:
        if attr not in EXPECTED_ROOT_ATTRS:
            validation_results.unexpected_root_attrs.add(attr)
    
    # Validate root-level child tags
    logger.debug("Validating root element child tags")
    for child in root_elem:
        if child.tag not in EXPECTED_ROOT_TAGS:
            validation_results.unexpected_root_tags[child.tag] += 1


def validate_channel_element(channel_elem: _Element, validation_results: ValidationResults = None) -> str:
    """Function to validate channel element structure and return channel_id."""
    if validation_results is None:
        validation_results = ValidationResults()
    
    logger.debug("Validating channel element attributes")
    channel_id = channel_elem.attrib.get("id", "Unknown")

    # Validate channel attributes
    for attr in channel_elem.attrib:
        if attr not in EXPECTED_CHANNEL_ATTRS:
            validation_results.unexpected_channel_attrs[channel_id].add(attr)

    # Validate channel child tags
    for child in channel_elem:
        if child.tag not in EXPECTED_CHANNEL_CHILD_TAGS:
            validation_results.unexpected_channel_tags[child.tag] += 1

    return channel_id


def validate_programme_element(programme_elem: _Element, validation_results: ValidationResults = None) -> str:
    """Function to validate programme element structure and return programme_id."""
    if validation_results is None:
        validation_results = ValidationResults()
    
    logger.debug("Validating programme element attributes")
    programme_id = programme_elem.attrib.get("program-id") or programme_elem.attrib.get(
        "channel", "Unknown"
    )
    if programme_id == "":
        programme_id = "Unknown"

    # Validate programme attributes
    for attr in programme_elem.attrib:
        if attr not in EXPECTED_PROGRAMME_ATTRS:
            validation_results.unexpected_programme_attrs[programme_id].add(attr)

    # Validate programme child tags
    for child in programme_elem:
        if child.tag not in EXPECTED_PROGRAMME_CHILD_TAGS:
            validation_results.unexpected_programme_tags[child.tag] += 1

    return programme_id


def get_root_and_validate(epg_file: str) -> _Element:
    """Read an EPG file and return the root element."""
    try:
        tree = etree.parse(epg_file)
    except OSError as e:
        logger.exception("File not found")
        raise FileNotFoundError(f"EPG file {epg_file} not found") from e

    root = tree.getroot()

    if root.tag != "tv":
        raise ValueError("Expected root tag 'tv', found '%s'" % root.tag)

    validate_root_element(root, validation_results)
    validate_root_tags(root)

    return root


def validate_root_tags(root: _Element):
    """Validate the root element of an EPG file."""
    # Validate root-level tags
    for child in root:
        if child.tag not in EXPECTED_ROOT_TAGS:
            validation_results.unexpected_root_tags[child.tag] += 1


def parse_epg_for_channels(
    epg_file: str, source: str, task_id: str | None = None
) -> list[EpgChannel]:
    """Parse an EPG file  and return a list of Channel objects."""
    logger.info("Parsing EPG file for channels: %s", epg_file)

    if task_id:
        IngestTaskManager.update_step_progress(task_id, 2, "Parsing EPG channels", 0)

    # Parse the entire tree at once
    root = get_root_and_validate(epg_file)

    channels = []

    # Process all channel elements
    for channel_elem in root.findall("channel"):
        channel_id = validate_channel_element(channel_elem, validation_results)

        try:
            channel_name = get_required_text(
                channel_elem, "display-name", context=channel_id
            )
            # Optional fields - use findtext for non-required elements
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
            logger.warning("Skipping invalid channel: %s", e)
        except Exception:
            logger.exception("Unexpected error parsing channel")

    # Log validation results
    validation_results.log_results("Channel Parsing")

    return channels


def parse_epg_for_programs(
    epg_file: str, source: str, source_timezone: str, task_id: str | None = None
) -> list[Program]:
    """Parse an EPG file and return a list of Program objects."""
    logger.info("Parsing EPG file for programs: %s", epg_file)

    if task_id:
        IngestTaskManager.update_step_progress(task_id, 4, "Parsing EPG programs", 0)

    # Parse the entire tree at once
    root = get_root_and_validate(epg_file)

    programs = []

    # Process all programme elements
    for programme_elem in root.findall("programme"):
        programme_id = validate_programme_element(programme_elem, validation_results)

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

            # parse timestamps in formats: 1751953500
            # time-zone aware based on source's timezone, will be set to UTC
            start_time = parse_program_time(start_time, source_timezone)
            end_time = parse_program_time(end_time, source_timezone)

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
            logger.warning("Skipping invalid programme: %s", e)
        except Exception:
            logger.exception("Unexpected error parsing programme")

    # Log validation results
    validation_results.log_results("Programme Parsing")

    return programs


def get_required_text(elem: _Element, tag: str, context: str = "") -> str:
    """Get the text of a required child tag. Raises ValueError if missing or empty."""
    logger.debug("Getting required text for tag: %s", tag)
    value = elem.findtext(tag)
    if not value or not value.strip():
        line = getattr(elem, "sourceline", "unknown")
        msg = f"Missing required <{tag}> at line {line}. Context: {context}"
        raise ValueError(msg)
    return value.strip()


def get_required_attr(elem: _Element, attr: str, context: str = "") -> str:
    """Get a required attribute. Raises ValueError if missing or empty."""
    logger.debug("Getting required attribute: %s", attr)
    value = elem.attrib.get(attr)
    if not value or not value.strip():
        line = getattr(elem, "sourceline", "unknown")
        msg = f"Missing required attribute '{attr}' at line {line}. Context: {context}"
        raise ValueError(msg)
    return value.strip()


def parse_program_time(ts_str: str, source_tz_str: str = "UTC") -> dt.datetime:
    """
    Interpret the Unix timestamp as a local time in the source timezone,
    and convert it to UTC.
    """
    ts = int(ts_str)

    # Step 1: convert to naive datetime (assume it's local time, not real UTC)
    naive_dt = dt.datetime.utcfromtimestamp(ts)

    # Step 2: assign the source's timezone to this naive datetime
    source_tz = pytz.timezone(source_tz_str)
    local_dt = source_tz.localize(naive_dt)

    # Step 3: convert to real UTC
    return local_dt.astimezone(pytz.UTC)
