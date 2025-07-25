"""Tests for load_m3u_channels_async function in M3U loader."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from ingest.m3u_loader import load_m3u_channels_async, LoadResult
from models.models import M3uChannel


class TestLoadM3uChannelsAsync:
    """Test cases for load_m3u_channels_async function."""

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.parse_m3u")
    @patch("ingest.m3u_loader._bulk_upsert_m3u_channels")
    @patch("ingest.m3u_loader.TaskManager")
    @patch("ingest.m3u_loader.IngestTaskManager")
    async def test_load_m3u_channels_async_success(
        self,
        mock_itm,
        mock_tm,
        mock_bulk_upsert,
        mock_parse_m3u,
        mock_session,
        sample_m3u_channels,
    ):
        """Test successful loading of M3U channels with task tracking."""
        # Setup mocks
        mock_parse_m3u.return_value = sample_m3u_channels

        # Mock bulk_upsert to return results based on actual batch size
        def mock_bulk_upsert_side_effect(session, batch):
            return [
                LoadResult(
                    "M3U_CHANNEL",
                    f"test_source:{channel.tvg_id}",
                    "upserted",
                    f"Channel {channel.tvg_id} loaded",
                )
                for channel in batch
            ]

        mock_bulk_upsert.side_effect = mock_bulk_upsert_side_effect

        file_path = "/test/file.m3u"
        source_name = "test_source"
        task_id = "test_task_123"

        # Execute async generator
        results = []
        async for result in load_m3u_channels_async(
            mock_session, file_path, source_name, task_id, batch_size=2
        ):
            results.append(result)

        # Verify parsing was called
        mock_parse_m3u.assert_called_once_with(file_path, source_name, task_id)

        # Verify task management calls
        mock_tm.update_total_items.assert_called_once_with(task_id, "ingest", 3)
        mock_itm.update_item_progress.assert_any_call(
            task_id, "Loading M3U channels...", 0
        )
        mock_itm.update_step_progress.assert_called_with(task_id, 3, "Loading", 0)

        # Verify bulk upsert calls (2 batches: [0:2], [2:3])
        assert mock_bulk_upsert.call_count == 2

        # Verify results
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.record_id == f"test_source:channel{i + 1}"
            assert result.status == "upserted"

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.parse_m3u")
    @patch("ingest.m3u_loader._bulk_upsert_m3u_channels")
    async def test_load_m3u_channels_async_without_task_id(
        self, mock_bulk_upsert, mock_parse_m3u, mock_session, sample_m3u_channels
    ):
        """Test loading M3U channels without task tracking."""
        # Setup mocks
        mock_parse_m3u.return_value = sample_m3u_channels
        mock_bulk_upsert.return_value = [
            LoadResult(
                "M3U_CHANNEL",
                f"test_source:channel{i + 1}",
                "upserted",
                f"Channel {i + 1} loaded",
            )
            for i in range(3)
        ]

        file_path = "/test/file.m3u"
        source_name = "test_source"

        # Execute async generator without task_id
        results = []
        async for result in load_m3u_channels_async(
            mock_session, file_path, source_name
        ):
            results.append(result)

        # Verify parsing was called without task_id
        mock_parse_m3u.assert_called_once_with(file_path, source_name, None)

        # Verify results
        assert len(results) == 3

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.parse_m3u")
    @patch("ingest.m3u_loader._bulk_upsert_m3u_channels")
    @patch("ingest.m3u_loader.IngestTaskManager")
    async def test_load_m3u_channels_async_progress_updates(
        self, mock_itm, mock_bulk_upsert, mock_parse_m3u, mock_session
    ):
        """Test progress updates during channel loading."""
        # Create 250 channels to test progress updates (every 100)
        large_batch = [
            M3uChannel(
                source="test_source",
                tvg_id=f"channel_{i:03d}",
                name=f"Channel {i}",
                stream_url=f"http://example.com/stream_{i}.m3u8",
                logo_url=f"http://example.com/logo_{i}.png",
                group="Test",
                stream_mode="live",
            )
            for i in range(250)
        ]

        mock_parse_m3u.return_value = large_batch
        mock_bulk_upsert.return_value = [
            LoadResult(
                "M3U_CHANNEL",
                f"test_source:channel_{i:03d}",
                "upserted",
                f"Channel {i} loaded",
            )
            for i in range(len(large_batch))
        ]

        task_id = "progress_test_task"

        # Execute async generator
        results = []
        async for result in load_m3u_channels_async(
            mock_session, "/test/file.m3u", "test_source", task_id, batch_size=1000
        ):
            results.append(result)

        # Verify progress updates were called at 100 and 200 intervals
        progress_calls = [
            call
            for call in mock_itm.update_item_progress.call_args_list
            if "Loaded" in str(call)
        ]
        assert len(progress_calls) >= 2  # At least updates at 100 and 200

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.parse_m3u")
    async def test_load_m3u_channels_async_empty_file(
        self, mock_parse_m3u, mock_session, empty_m3u_channels
    ):
        """Test loading empty M3U file."""
        mock_parse_m3u.return_value = empty_m3u_channels

        results = []
        async for result in load_m3u_channels_async(
            mock_session, "/test/empty.m3u", "test_source"
        ):
            results.append(result)

        # Verify no results for empty file
        assert len(results) == 0

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.parse_m3u")
    async def test_load_m3u_channels_async_parse_error(
        self, mock_parse_m3u, mock_session
    ):
        """Test handling of parsing errors."""
        # Mock parsing error
        mock_parse_m3u.side_effect = ValueError("Invalid M3U format")

        results = []
        async for result in load_m3u_channels_async(
            mock_session, "/test/invalid.m3u", "test_source"
        ):
            results.append(result)

        # Verify error result
        assert len(results) == 1
        result = results[0]
        assert result.record_type == "M3U_CHANNEL"
        assert result.record_id == "BATCH"
        assert result.status == "error"
        assert "Invalid M3U format" in result.message

        # Verify rollback and error logging
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.parse_m3u")
    @patch("ingest.m3u_loader._bulk_upsert_m3u_channels")
    async def test_load_m3u_channels_async_bulk_upsert_error(
        self, mock_bulk_upsert, mock_parse_m3u, mock_session, sample_m3u_channels
    ):
        """Test handling of bulk upsert errors."""
        mock_parse_m3u.return_value = sample_m3u_channels
        mock_bulk_upsert.side_effect = SQLAlchemyError("Database error")

        results = []
        async for result in load_m3u_channels_async(
            mock_session, "/test/file.m3u", "test_source"
        ):
            results.append(result)

        # Verify error result
        assert len(results) == 1
        result = results[0]
        assert result.status == "error"
        assert "Database error" in result.message

        # Verify rollback
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.parse_m3u")
    @patch("ingest.m3u_loader._bulk_upsert_m3u_channels")
    @patch("ingest.m3u_loader.asyncio.sleep")
    async def test_load_m3u_channels_async_batch_processing(
        self, mock_sleep, mock_bulk_upsert, mock_parse_m3u, mock_session
    ):
        """Test batch processing with custom batch size."""
        # Create 7 channels to test batching with batch_size=3
        channels = [
            M3uChannel(
                source="test_source",
                tvg_id=f"channel_{i}",
                name=f"Channel {i}",
                stream_url=f"http://example.com/stream_{i}.m3u8",
                logo_url=f"http://example.com/logo_{i}.png",
                group="Test",
                stream_mode="live",
            )
            for i in range(7)
        ]

        mock_parse_m3u.return_value = channels

        # Mock bulk upsert to return results matching input
        def mock_bulk_upsert_side_effect(session, batch):
            return [
                LoadResult(
                    "M3U_CHANNEL",
                    f"test_source:{ch.tvg_id}",
                    "upserted",
                    f"{ch.name} loaded",
                )
                for ch in batch
            ]

        mock_bulk_upsert.side_effect = mock_bulk_upsert_side_effect

        results = []
        async for result in load_m3u_channels_async(
            mock_session, "/test/file.m3u", "test_source", batch_size=3
        ):
            results.append(result)

        # Verify 3 batches: [0:3], [3:6], [6:7]
        assert mock_bulk_upsert.call_count == 3

        # Verify batch sizes
        call_args_list = mock_bulk_upsert.call_args_list
        assert len(call_args_list[0][0][1]) == 3  # First batch: 3 channels
        assert len(call_args_list[1][0][1]) == 3  # Second batch: 3 channels
        assert len(call_args_list[2][0][1]) == 1  # Third batch: 1 channel

        # Verify all results
        assert len(results) == 7

        # Verify asyncio.sleep was called for yielding control
        assert mock_sleep.call_count == 3

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.parse_m3u")
    @patch("ingest.m3u_loader._bulk_upsert_m3u_channels")
    async def test_load_m3u_channels_async_unicode_handling(
        self, mock_bulk_upsert, mock_parse_m3u, mock_session, unicode_m3u_channel
    ):
        """Test loading M3U channels with unicode characters."""
        mock_parse_m3u.return_value = [unicode_m3u_channel]
        mock_bulk_upsert.return_value = [
            LoadResult(
                "M3U_CHANNEL",
                "unicode_source:unicode_channel",
                "upserted",
                "Unicode channel loaded",
            )
        ]

        results = []
        async for result in load_m3u_channels_async(
            mock_session, "/test/unicode.m3u", "unicode_source"
        ):
            results.append(result)

        # Verify unicode channel was processed
        assert len(results) == 1
        assert results[0].record_id == "unicode_source:unicode_channel"
        assert results[0].status == "upserted"

    @pytest.mark.parametrize("batch_size", [1, 10, 100, 1000])
    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.parse_m3u")
    @patch("ingest.m3u_loader._bulk_upsert_m3u_channels")
    async def test_load_m3u_channels_async_different_batch_sizes(
        self, mock_bulk_upsert, mock_parse_m3u, mock_session, batch_size
    ):
        """Test loading with different batch sizes."""
        # Create 50 channels
        channels = [
            M3uChannel(
                source="test_source",
                tvg_id=f"channel_{i:02d}",
                name=f"Channel {i}",
                stream_url=f"http://example.com/stream_{i}.m3u8",
                logo_url=f"http://example.com/logo_{i}.png",
                group="Test",
                stream_mode="live",
            )
            for i in range(50)
        ]

        mock_parse_m3u.return_value = channels

        def mock_bulk_upsert_side_effect(session, batch):
            return [
                LoadResult(
                    "M3U_CHANNEL",
                    f"test_source:{ch.tvg_id}",
                    "upserted",
                    f"{ch.name} loaded",
                )
                for ch in batch
            ]

        mock_bulk_upsert.side_effect = mock_bulk_upsert_side_effect

        results = []
        async for result in load_m3u_channels_async(
            mock_session, "/test/file.m3u", "test_source", batch_size=batch_size
        ):
            results.append(result)

        # Verify all channels processed regardless of batch size
        assert len(results) == 50

        # Verify expected number of batch calls
        expected_batches = (50 + batch_size - 1) // batch_size  # Ceiling division
        assert mock_bulk_upsert.call_count == expected_batches
