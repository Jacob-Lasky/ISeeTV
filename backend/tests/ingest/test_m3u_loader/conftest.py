"""Shared fixtures for M3U loader tests."""

import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from models.models import M3uChannel


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session for database operations."""
    session = Mock(spec=Session)
    session.execute = Mock()
    session.commit = Mock()
    session.rollback = Mock()
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
        stream_mode="live"
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
            stream_mode="live"
        ),
        M3uChannel(
            source="test_source",
            tvg_id="channel2",
            name="Test Channel 2",
            stream_url="http://example.com/stream2.m3u8",
            logo_url="http://example.com/logo2.png",
            group="Sports",
            stream_mode="live"
        ),
        M3uChannel(
            source="test_source",
            tvg_id="channel3",
            name="Test Channel 3",
            stream_url="http://example.com/stream3.m3u8",
            logo_url=None,
            group=None,
            stream_mode="on_demand"
        )
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
        stream_mode="live"
    )


@pytest.fixture
def empty_m3u_channels():
    """Empty list of M3U channels for edge case testing."""
    return []


@pytest.fixture
def mock_logger():
    """Mock logger for testing logging behavior."""
    return Mock()


@pytest.fixture
def mock_task_manager():
    """Mock task manager for testing progress tracking."""
    mock_tm = Mock()
    mock_tm.update_total_items = Mock()
    return mock_tm


@pytest.fixture
def mock_ingest_task_manager():
    """Mock ingest task manager for testing progress tracking."""
    mock_itm = Mock()
    mock_itm.update_item_progress = Mock()
    mock_itm.update_step_progress = Mock()
    return mock_itm
