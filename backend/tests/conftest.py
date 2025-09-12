"""Shared fixtures for all ISeeTV tests."""

import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List
from io import StringIO
import lxml.etree as et

from models.models import M3uChannel, EpgChannel, Program
from models.stream_models import StreamChannel
from ingest.epg_loader import LoadResult


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session for database operations."""
    session = Mock(spec=Session)
    session.execute = Mock()
    session.commit = Mock()
    session.rollback = Mock()

    # Mock execute result with rowcount
    mock_result = Mock()
    mock_result.rowcount = 1
    session.execute.return_value = mock_result

    return session


@pytest.fixture
def sample_m3u_channel():
    """Sample M3U channel for testing."""
    return M3uChannel(
        source="test_source",
        tvg_id="channel1",
        name="Test Channel",
        stream_url="http://example.com/stream.m3u8",
        logo_url="http://example.com/logo.png",
        group="Entertainment",
        stream_mode="live",
    )


@pytest.fixture
def sample_m3u_channels():
    """List of sample M3U channels for batch testing."""
    return [
        M3uChannel(
            source="test_source",
            tvg_id="channel1",
            name="Test Channel 1",
            stream_url="http://example.com/stream1.m3u8",
            logo_url="http://example.com/logo1.png",
            group="Entertainment",
            stream_mode="live",
        ),
        M3uChannel(
            source="test_source",
            tvg_id="channel2",
            name="Test Channel 2",
            stream_url="http://example.com/stream2.m3u8",
            logo_url="http://example.com/logo2.png",
            group="Sports",
            stream_mode="live",
        ),
        M3uChannel(
            source="test_source",
            tvg_id="channel3",
            name="Test Channel 3",
            stream_url="http://example.com/stream3.m3u8",
            logo_url=None,
            group=None,
            stream_mode="on_demand",
        ),
    ]


@pytest.fixture
def unicode_m3u_channel():
    """M3U channel with unicode characters for edge case testing."""
    return M3uChannel(
        source="unicode_source",
        tvg_id="unicode_channel",
        name="测试频道 🎬",
        stream_url="http://example.com/unicode_stream.m3u8",
        logo_url="http://example.com/unicode_logo.png",
        group="国际频道",
        stream_mode="live",
    )


@pytest.fixture
def empty_m3u_channels():
    """Empty list of M3U channels for edge case testing."""
    return []


# EPG-related fixtures
@pytest.fixture
def sample_epg_channel():
    """Sample EPG channel for testing."""
    return EpgChannel(
        source="test_source",
        channel_id="channel1",
        display_name="Test Channel",
        icon_url="http://example.com/icon.png",
    )


@pytest.fixture
def sample_epg_channel_with_none():
    """Sample EPG channel for testing."""
    return EpgChannel(
        source="test_source",
        channel_id="channel1",
        display_name="Test Channel",
        icon_url=None,
    )


@pytest.fixture
def sample_epg_channels():
    """List of sample EPG channels for batch testing."""
    return [
        EpgChannel(
            source="test_source",
            channel_id="channel1",
            display_name="Test Channel 1",
            icon_url="http://example.com/icon1.png",
        ),
        EpgChannel(
            source="test_source",
            channel_id="channel2",
            display_name="Test Channel 2",
            icon_url="http://example.com/icon2.png",
        ),
        EpgChannel(
            source="test_source",
            channel_id="channel3",
            display_name="Test Channel 3",
            icon_url=None,  # Test None icon_url
        ),
    ]


@pytest.fixture
def sample_program():
    """Sample program for testing."""
    return Program(
        source="test_source",
        program_id="prog1",
        channel_id="channel1",
        start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
        title="Test Program",
        description="Test program description",
    )


@pytest.fixture
def sample_programs():
    """List of sample programs for batch testing."""
    return [
        Program(
            source="test_source",
            program_id="prog1",
            channel_id="channel1",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            title="Test Program 1",
            description="Test program 1 description",
        ),
        Program(
            source="test_source",
            program_id="prog2",
            channel_id="channel1",
            start_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
            title="Test Program 2",
            description="Test program 2 description",
        ),
        Program(
            source="test_source",
            program_id="prog3",
            channel_id="channel2",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            title="Test Program 3",
            description=None,  # Test None description
        ),
    ]


@pytest.fixture
def unicode_epg_channel():
    """EPG channel with unicode characters for edge case testing."""
    return EpgChannel(
        source="test_source",
        channel_id="unicode_channel",
        display_name="Tëst Chännél 中文",
        icon_url="http://example.com/ïcön.png",
    )


@pytest.fixture
def unicode_program():
    """Program with unicode characters for edge case testing."""
    return Program(
        source="test_source",
        program_id="unicode_prog",
        channel_id="unicode_channel",
        start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
        title="Tëst Prögräm 中文",
        description="Tëst prögräm dëscriptïön 中文",
    )


@pytest.fixture
def empty_epg_channels():
    """Empty list of EPG channels for edge case testing."""
    return []


@pytest.fixture
def empty_programs():
    """Empty list of programs for edge case testing."""
    return []


@pytest.fixture
def sample_epg_xml_content():
    """Sample EPG XML content for file-based testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<tv>
    <channel id="channel1">
        <display-name>Test Channel 1</display-name>
        <icon src="http://example.com/icon1.png"/>
    </channel>
    <channel id="channel2">
        <display-name>Test Channel 2</display-name>
        <icon src="http://example.com/icon2.png"/>
    </channel>
    <programme start="20240101120000 +0000" stop="20240101130000 +0000" channel="channel1">
        <title>Test Program 1</title>
        <desc>Test program 1 description</desc>
    </programme>
    <programme start="20240101130000 +0000" stop="20240101140000 +0000" channel="channel1">
        <title>Test Program 2</title>
        <desc>Test program 2 description</desc>
    </programme>
</tv>"""


@pytest.fixture
def create_temp_epg_file(tmp_path):
    """Factory fixture to create temporary EPG files for testing."""

    def _create_file(content: str, filename: str = "test.xml") -> str:
        file_path = tmp_path / filename
        file_path.write_text(content, encoding="utf-8")
        return str(file_path)

    return _create_file


@pytest.fixture
def temp_epg_file(tmp_path, sample_epg_xml_content):
    """Create a temporary EPG file with sample content for testing."""
    file_path = tmp_path / "test_epg.xml"
    file_path.write_text(sample_epg_xml_content, encoding="utf-8")
    return str(file_path)


@pytest.fixture
def create_temp_epg_file_with_data(tmp_path):
    """Factory fixture to create EPG files with specified number of channels and programs."""
    
    def _create_file(source: str, num_channels: int, num_programs: int, filename: str = "test.xml") -> str:
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n'
        
        # Add channels
        for i in range(num_channels):
            xml_content += f'''    <channel id="channel{i}">
        <display-name>Test Channel {i}</display-name>
        <icon src="http://example.com/icon{i}.png"/>
    </channel>
'''
        
        # Add programs
        for i in range(num_programs):
            channel_id = f"channel{i % num_channels}" if num_channels > 0 else "channel0"
            start_time = f"2024010{i % 9 + 1}120000 +0000"
            stop_time = f"2024010{i % 9 + 1}130000 +0000"
            xml_content += f'''    <programme start="{start_time}" stop="{stop_time}" channel="{channel_id}">
        <title>Test Program {i}</title>
        <desc>Test program {i} description</desc>
    </programme>
'''
        
        xml_content += '</tv>'
        
        file_path = tmp_path / filename
        file_path.write_text(xml_content, encoding="utf-8")
        return str(file_path)
    
    return _create_file


@pytest.fixture
def patch_etree_parse(tmp_path):
    """Create temporary XML files for testing etree.parse without mocking."""

    def _create_temp_xml(xml_str: str):
        # Create a temporary XML file with the provided content
        temp_file = tmp_path / "test.xml"
        temp_file.write_text(xml_str, encoding="utf-8")
        return str(temp_file)

    return _create_temp_xml

@pytest.fixture
def mock_stream_channel():
    """Mock StreamChannel object for testing."""
    return StreamChannel(
        m3u_id=1,
        source="test_source",
        tvg_id="ch001",
        name="Test Channel",
        stream_url="http://example.com/stream.m3u8",
        logo_url="http://example.com/logo.png",
        group="Entertainment",
        stream_mode="live",
        epg_id=2,
        display_name="Test Channel Display",
        icon_url="http://example.com/icon.png",
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 2, 12, 0, 0),
        filter_reasons=[],
        program_count=5,
        next_program_title="Next Program",
        next_program_start=datetime(2024, 1, 3, 15, 0, 0)
    )

@pytest.fixture
def mock_filter_counts():
    """Mock filter view counts for testing."""
    return {
        "normal": 100,
        "inverse": 50,
        "all": 150
    }

@pytest.fixture
def mock_filter_values():
    """Mock filter values for testing."""
    return {
        "source": [
            {"value": "source1", "count": 10},
            {"value": "source2", "count": 15},
            {"value": "source3", "count": 8}
        ],
        "group": [
            {"value": "Entertainment", "count": 20},
            {"value": "Sports", "count": 12},
            {"value": "News", "count": 5}
        ],
        "display_name": [
            {"value": "Channel 1", "count": 1},
            {"value": "Channel 2", "count": 1},
            {"value": "Channel 3", "count": 1}
        ]
    }