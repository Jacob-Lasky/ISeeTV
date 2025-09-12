"""Tests for _bulk_upsert_epg_channels function following atomic design principles."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.exc import SQLAlchemyError

from ingest.epg_loader import _bulk_upsert_epg_channels, LoadResult


class TestBulkUpsertEpgChannels:
    """Test _bulk_upsert_epg_channels function functionality."""

    @pytest.mark.asyncio
    async def test_bulk_upsert_epg_channels_success(self, mock_session, sample_epg_channels):
        """Test successful bulk EPG channel upsert."""
        results = await _bulk_upsert_epg_channels(mock_session, sample_epg_channels)

        # Verify database interactions
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

        # Verify results
        assert len(results) == 3
        for i, result in enumerate(results):
            assert isinstance(result, LoadResult)
            assert result.record_type == "EPG_CHANNEL"
            assert result.record_id == f"test_source:channel{i+1}"
            assert result.status == "upserted"
            assert f"Test Channel {i+1}" in result.message

    @pytest.mark.asyncio
    async def test_bulk_upsert_epg_channels_empty_list(self, mock_session, empty_epg_channels):
        """Test bulk EPG channel upsert with empty list."""
        results = await _bulk_upsert_epg_channels(mock_session, empty_epg_channels)

        # Verify no database operations
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

        # Verify empty results
        assert results == []

    @pytest.mark.asyncio
    async def test_bulk_upsert_epg_channels_single_channel(self, mock_session, sample_epg_channel):
        """Test bulk EPG channel upsert with single channel."""
        results = await _bulk_upsert_epg_channels(mock_session, [sample_epg_channel])

        # Verify database interactions
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

        # Verify single result
        assert len(results) == 1
        assert results[0].status == "upserted"
        assert results[0].record_id == "test_source:channel1"

    @pytest.mark.asyncio
    async def test_bulk_upsert_epg_channels_with_unicode(self, mock_session, unicode_epg_channel):
        """Test bulk EPG channel upsert with unicode characters."""
        results = await _bulk_upsert_epg_channels(mock_session, [unicode_epg_channel])

        assert len(results) == 1
        assert results[0].status == "upserted"
        assert "Tëst Chännél 中文" in results[0].message

    @pytest.mark.asyncio
    async def test_bulk_upsert_epg_channels_database_error(self, mock_session, sample_epg_channels):
        """Test bulk EPG channel upsert with database error."""
        # Mock database error
        mock_session.execute.side_effect = SQLAlchemyError("Database connection failed")

        results = await _bulk_upsert_epg_channels(mock_session, sample_epg_channels)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()

        # Verify error results for all channels
        assert len(results) == 3
        for result in results:
            assert result.status == "error"
            assert "Database connection failed" in result.message

    @pytest.mark.asyncio
    async def test_bulk_upsert_epg_channels_generic_exception(self, mock_session, sample_epg_channels):
        """Test bulk EPG channel upsert with generic exception."""
        # Mock generic exception
        mock_session.execute.side_effect = Exception("Unexpected error")

        results = await _bulk_upsert_epg_channels(mock_session, sample_epg_channels)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()

        # Verify error results
        assert len(results) == 3
        for result in results:
            assert result.status == "error"
            assert "Unexpected error" in result.message

    @pytest.mark.asyncio
    async def test_bulk_upsert_epg_channels_commit_error(self, mock_session, sample_epg_channels):
        """Test bulk EPG channel upsert with commit error."""
        # Mock commit error
        mock_session.commit.side_effect = SQLAlchemyError("Commit failed")

        results = await _bulk_upsert_epg_channels(mock_session, sample_epg_channels)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()

        # Verify error results
        assert len(results) == 3
        for result in results:
            assert result.status == "error"
            assert "Commit failed" in result.message
            
    @pytest.mark.asyncio
    async def test_bulk_upsert_epg_channels_data_structure(self, mock_session, sample_epg_channels):
        """Test that the data structure passed to execute is correct."""
        await _bulk_upsert_epg_channels(mock_session, sample_epg_channels)

        # Verify execute was called with statement and data
        args, kwargs = mock_session.execute.call_args
        stmt, data = args

        # Verify data structure
        assert len(data) == 3
        for i, channel_data in enumerate(data):
            assert channel_data["source"] == "test_source"
            assert channel_data["channel_id"] == f"channel{i+1}"
            assert channel_data["display_name"] == f"Test Channel {i+1}"

    @pytest.mark.asyncio
    async def test_bulk_upsert_epg_channels_with_none_values(self, mock_session):
        """Test bulk EPG channel upsert with None values."""
        from models.models import EpgChannel
        
        channels = [
            EpgChannel(
                source="test_source",
                channel_id="channel1",
                display_name="Test Channel",
                icon_url=None
            )
        ]

        results = await _bulk_upsert_epg_channels(mock_session, channels)

        assert len(results) == 1
        assert results[0].status == "upserted"

        # Verify data structure includes None values
        args, kwargs = mock_session.execute.call_args
        stmt, data = args
        assert data[0]["icon_url"] is None

    @pytest.mark.asyncio
    async def test_bulk_upsert_epg_channels_large_batch(self, mock_session):
        """Test bulk EPG channel upsert with large batch."""
        from models.models import EpgChannel
        
        # Create large batch of channels
        large_batch = [
            EpgChannel(
                source="test_source",
                channel_id=f"channel{i}",
                display_name=f"Test Channel {i}",
                icon_url=f"http://example.com/icon{i}.png"
            )
            for i in range(1000)
        ]

        results = await _bulk_upsert_epg_channels(mock_session, large_batch)

        # Verify all channels processed
        assert len(results) == 1000
        for i, result in enumerate(results):
            assert result.record_id == f"test_source:channel{i}"
            assert result.status == "upserted"

        # Verify single database operation
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_upsert_epg_channels_mixed_data_types(self, mock_session):
        """Test bulk EPG channel upsert with mixed data types."""
        from models.models import EpgChannel
        
        channels = [
            EpgChannel(
                source="test_source",
                channel_id="channel1",
                display_name="Normal Channel",
                icon_url="http://example.com/icon.png"
            ),
            EpgChannel(
                source="test_source",
                channel_id="channel2",
                display_name="",  # Empty string
                icon_url=None  # None value
            ),
            EpgChannel(
                source="test_source",
                channel_id="channel3",
                display_name="Unicode Chännél 中文",
                icon_url="http://example.com/ïcön.png"
            )
        ]

        results = await _bulk_upsert_epg_channels(mock_session, channels)

        assert len(results) == 3
        for result in results:
            assert result.status == "upserted"
