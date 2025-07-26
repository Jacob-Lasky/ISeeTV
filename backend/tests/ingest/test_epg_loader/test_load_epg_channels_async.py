"""Tests for load_epg_channels_async function following atomic design principles."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from ingest.epg_loader import load_epg_channels_async, LoadResult


class TestLoadEpgChannelsAsync:
    """Test load_epg_channels_async async generator function functionality."""

    @pytest.mark.asyncio
    async def test_load_epg_channels_async_success(
        self, mock_session, patch_etree_parse, sample_epg_xml_content
    ):
        """Test successful async loading of EPG channels."""
        # Mock successful upsert results - should return list of LoadResult objects
        with patch("ingest.epg_loader._bulk_upsert_epg_channels") as mock_bulk_upsert:
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="EPG_CHANNEL",
                    record_id="test_source:channel1",
                    status="upserted",
                    message="Channel 'Test Channel 1' processed",
                ),
                LoadResult(
                    record_type="EPG_CHANNEL",
                    record_id="test_source:channel2",
                    status="upserted",
                    message="Channel 'Test Channel 2' processed",
                ),
            ]

            results = []
            temp_xml_file = patch_etree_parse(sample_epg_xml_content)
            async for result in load_epg_channels_async(
                mock_session, temp_xml_file, "test_source"
            ):
                results.append(result)

            # Verify results - should get 2 LoadResult objects
            assert len(results) == 2
            assert all(result.status == "upserted" for result in results)
            assert "Test Channel 1" in results[0].message
            assert "Test Channel 2" in results[1].message

            # Verify bulk upsert was called with parsed channels
            mock_bulk_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_epg_channels_async_empty_list(self, mock_session, patch_etree_parse):
        """Test async loading with empty channel list."""
        # Create XML with no channels
        empty_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tv>
</tv>'''
        
        results = []
        async for result in load_epg_channels_async(
            mock_session, patch_etree_parse(empty_xml_content), "test_source"
        ):
            results.append(result)

        # Should yield nothing for empty list
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_load_epg_channels_async_with_task_id(
        self, mock_session, patch_etree_parse, sample_epg_xml_content
    ):
        """Test async loading with task manager progress updates."""
        with patch("ingest.epg_loader._bulk_upsert_epg_channels") as mock_bulk_upsert:
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="EPG_CHANNELS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="3 channels upserted",
                )
            ]

            results = []
            async for result in load_epg_channels_async(
                mock_session,
                patch_etree_parse(sample_epg_xml_content),
                "test_source",
                task_id="TEST123",
            ):
                results.append(result)

    @pytest.mark.asyncio
    async def test_load_epg_channels_async_batch_processing(
        self, mock_session, patch_etree_parse
    ):
        """Test async loading with large batch requiring multiple operations."""
        # Create XML with multiple channels to simulate batch processing
        batch_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tv>
'''
        for i in range(5):  # Create 5 channels for testing
            batch_xml_content += f'''    <channel id="channel{i}">
        <display-name>Channel {i}</display-name>
        <icon src="http://example.com/icon{i}.png" />
    </channel>
'''
        batch_xml_content += '</tv>'

        with patch("ingest.epg_loader._bulk_upsert_epg_channels") as mock_bulk_upsert:
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="EPG_CHANNELS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="5 channels upserted",
                )
            ]

            results = []
            async for result in load_epg_channels_async(
                mock_session, patch_etree_parse(batch_xml_content), "test_source"
            ):
                results.append(result)

            # Should still process all channels
            assert len(results) == 1
            mock_bulk_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_epg_channels_async_error_handling(
        self, mock_session, patch_etree_parse, sample_epg_xml_content
    ):
        """Test async loading with error in bulk upsert."""
        with patch("ingest.epg_loader._bulk_upsert_epg_channels") as mock_bulk_upsert:
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="EPG_CHANNELS",
                    record_id="bulk_operation",
                    status="error",
                    message="Database error occurred",
                )
            ]

            results = []
            async for result in load_epg_channels_async(
                mock_session, patch_etree_parse(sample_epg_xml_content), "test_source"
            ):
                results.append(result)

            # Should still yield the error result
            assert len(results) == 1
            assert results[0].status == "error"
            assert "Database error" in results[0].message

    @pytest.mark.asyncio
    async def test_load_epg_channels_async_with_unicode_data(
        self, mock_session, patch_etree_parse
    ):
        """Test async loading with unicode characters in channel data."""
        # Create XML content with unicode characters
        unicode_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tv>
    <channel id="unicode_channel">
        <display-name>Tëst Chännél 中文</display-name>
        <icon src="http://example.com/ïcön.png" />
    </channel>
</tv>'''
        
        with patch("ingest.epg_loader._bulk_upsert_epg_channels") as mock_bulk_upsert:
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="EPG_CHANNELS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="1 channel upserted",
                )
            ]

            results = []
            async for result in load_epg_channels_async(
                mock_session, patch_etree_parse(unicode_xml_content), "test_source"
            ):
                results.append(result)

            assert len(results) == 1
            assert results[0].status == "upserted"

    @pytest.mark.asyncio
    async def test_load_epg_channels_async_progress_updates(
        self, mock_session, sample_epg_channels
    ):
        """Test that progress updates are called correctly."""
        with patch("ingest.epg_loader._bulk_upsert_epg_channels") as mock_bulk_upsert:
            mock_bulk_upsert.return_value = LoadResult(
                record_type="EPG_CHANNELS",
                record_id="bulk_operation",
                status="upserted",
                message="3 channels upserted",
            )

            results = []
            async for result in load_epg_channels_async(
                mock_session,
                sample_epg_channels,
                "test_source",
                task_id="TEST123",
            ):
                results.append(result)

    @pytest.mark.asyncio
    async def test_load_epg_channels_async_skipped_result(
        self, mock_session, patch_etree_parse, sample_epg_xml_content
    ):
        """Test async loading when bulk upsert returns skipped status."""
        with patch("ingest.epg_loader._bulk_upsert_epg_channels") as mock_bulk_upsert:
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="EPG_CHANNELS",
                    record_id="bulk_operation",
                    status="skipped",
                    message="No changes detected",
                )
            ]

            results = []
            async for result in load_epg_channels_async(
                mock_session, patch_etree_parse(sample_epg_xml_content), "test_source"
            ):
                results.append(result)

            assert len(results) == 1
            assert results[0].status == "skipped"

    @pytest.mark.asyncio
    async def test_load_epg_channels_async_generator_behavior(
        self, mock_session, sample_epg_channels
    ):
        """Test that the function behaves as an async generator."""
        with patch("ingest.epg_loader._bulk_upsert_epg_channels") as mock_bulk_upsert:
            mock_bulk_upsert.return_value = LoadResult(
                record_type="EPG_CHANNELS",
                record_id="bulk_operation",
                status="upserted",
                message="3 channels upserted",
            )

            # Test that it's an async generator
            gen = load_epg_channels_async(
                mock_session, sample_epg_channels, "test_source"
            )
            assert hasattr(gen, "__aiter__")
            assert hasattr(gen, "__anext__")

            # Test iteration
            result = await gen.__anext__()
            assert isinstance(result, LoadResult)

            # Test that StopAsyncIteration is raised when done
            with pytest.raises(StopAsyncIteration):
                await gen.__anext__()

    @pytest.mark.asyncio
    async def test_load_epg_channels_async_exception_handling(
        self, mock_session, patch_etree_parse, sample_epg_xml_content
    ):
        """Test async loading when bulk upsert raises an exception."""
        with patch("ingest.epg_loader._bulk_upsert_epg_channels") as mock_bulk_upsert:
            mock_bulk_upsert.side_effect = Exception("Unexpected error")

            async for result in load_epg_channels_async(
                mock_session,
                patch_etree_parse(sample_epg_xml_content),
                "test_source",
            ):
                pass

    @pytest.mark.asyncio
    async def test_load_epg_channels_async_single_channel(
        self, mock_session, patch_etree_parse, sample_epg_xml_content
    ):
        """Test async loading with single channel."""
        with patch("ingest.epg_loader._bulk_upsert_epg_channels") as mock_bulk_upsert:
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="EPG_CHANNEL",
                    record_id="test_source:channel1",
                    status="upserted",
                    message="Channel 'Test Channel 1' processed",
                ),
            ]

            results = []
            temp_xml_file = patch_etree_parse(sample_epg_xml_content)
            async for result in load_epg_channels_async(
                mock_session,
                temp_xml_file,
                "test_source",
            ):
                results.append(result)

            assert len(results) == 1
            assert results[0].status == "upserted"
            assert "Test Channel 1" in results[0].message

    @pytest.mark.asyncio
    async def test_load_epg_channels_async_task_id_none(
        self, mock_session, patch_etree_parse, sample_epg_xml_content
    ):
        """Test async loading with task_id parameter."""
        with patch("ingest.epg_loader._bulk_upsert_epg_channels") as mock_bulk_upsert:
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="EPG_CHANNEL",
                    record_id="test_source:channel1",
                    status="upserted",
                    message="Channel 'Test Channel 1' processed",
                ),
                LoadResult(
                    record_type="EPG_CHANNEL",
                    record_id="test_source:channel2",
                    status="upserted",
                    message="Channel 'Test Channel 2' processed",
                ),
            ]

            results = []
            temp_xml_file = patch_etree_parse(sample_epg_xml_content)
            async for result in load_epg_channels_async(
                mock_session, temp_xml_file, "test_source", task_id="TEST123"
            ):
                results.append(result)

            # Should work fine with task_id parameter
            assert len(results) == 2
            assert all(result.status == "upserted" for result in results)

    @pytest.mark.asyncio
    async def test_load_epg_channels_async_memory_efficiency(self, mock_session):
        """Test that the async generator doesn't load all results into memory at once."""
        from models.models import EpgChannel

        # Create a very large batch
        large_batch = []
        for i in range(10000):
            channel = EpgChannel(
                source="test_source",
                channel_id=f"channel{i}",
                display_name=f"Channel {i}",
                icon_url=f"http://example.com/icon{i}.png",
            )
            large_batch.append(channel)

        with patch("ingest.epg_loader._bulk_upsert_epg_channels") as mock_bulk_upsert:
            mock_bulk_upsert.return_value = LoadResult(
                record_type="EPG_CHANNELS",
                record_id="bulk_operation",
                status="upserted",
                message="10000 channels upserted",
            )

            # Should be able to iterate without memory issues
            result_count = 0
            async for result in load_epg_channels_async(
                mock_session, large_batch, "test_source"
            ):
                result_count += 1
                # Break early to test generator behavior
                if result_count >= 1:
                    break

            assert result_count == 1
