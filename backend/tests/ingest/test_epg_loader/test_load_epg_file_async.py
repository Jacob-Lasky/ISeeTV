"""
Comprehensive tests for load_epg_file_async function.

This module tests the main EPG file loading function that orchestrates
both channel and program loading in sequence.
"""

import pytest
from unittest.mock import patch, AsyncMock
from ingest.epg_loader import load_epg_file_async, LoadResult


class TestLoadEpgFileAsync:
    """Test cases for load_epg_file_async function."""

    @pytest.mark.asyncio
    async def test_load_epg_file_async_success_complete(
        self, mock_session, temp_epg_file
    ):
        """Test successful complete EPG file loading with channels and programs."""
        with patch(
            "ingest.epg_loader.load_epg_channels_async"
        ) as mock_load_channels, patch(
            "ingest.epg_loader.load_programs_async"
        ) as mock_load_programs:

            # Mock async generators
            async def mock_channels_gen():
                yield LoadResult(
                    "EPG_CHANNELS", "bulk", "upserted", "1 channels loaded"
                )

            async def mock_programs_gen():
                yield LoadResult("PROGRAMS", "bulk", "upserted", "1 programs loaded")

            mock_load_channels.return_value = mock_channels_gen()
            mock_load_programs.return_value = mock_programs_gen()

            results = []
            async for result in load_epg_file_async(
                mock_session,
                temp_epg_file,
                "test_source",
                "UTC",
            ):
                results.append(result)

            # Should get results from both loaders
            assert len(results) == 2
            assert results[0].record_type == "EPG_CHANNELS"
            assert results[1].record_type == "PROGRAMS"

            # Verify both loaders were called with correct parameters
            mock_load_channels.assert_called_once_with(mock_session, temp_epg_file, "test_source", None)
            mock_load_programs.assert_called_once_with(mock_session, temp_epg_file, "test_source", "UTC", None)

    @pytest.mark.asyncio
    async def test_load_epg_file_async_channels_only(self, mock_session, temp_epg_file):
        """Test EPG file loading with only channels, no programs."""
        with patch(
            "ingest.epg_loader.load_epg_channels_async"
        ) as mock_load_channels, patch(
            "ingest.epg_loader.load_programs_async"
        ) as mock_load_programs:

            async def mock_channels_gen():
                yield LoadResult(
                    "EPG_CHANNELS", "bulk", "upserted", "1 channels loaded"
                )

            # Mock channels to return results, programs to return nothing
            async def mock_empty_programs_gen():
                return
                yield  # This line will never execute, but makes it an async generator

            mock_load_channels.return_value = mock_channels_gen()
            mock_load_programs.return_value = mock_empty_programs_gen()

            results = []
            async for result in load_epg_file_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            # Should only have channel results
            assert len(results) == 1
            assert results[0].record_type == "EPG_CHANNELS"

            # Both loaders should be called
            mock_load_channels.assert_called_once_with(mock_session, temp_epg_file, "test_source", None)
            mock_load_programs.assert_called_once_with(mock_session, temp_epg_file, "test_source", "UTC", None)

    @pytest.mark.asyncio
    async def test_load_epg_file_async_programs_only(self, mock_session, temp_epg_file):
        """Test EPG file loading with only programs, no channels."""
        with patch(
            "ingest.epg_loader.load_epg_channels_async"
        ) as mock_load_channels, patch(
            "ingest.epg_loader.load_programs_async"
        ) as mock_load_programs:

            async def mock_programs_gen():
                yield LoadResult("PROGRAMS", "bulk", "upserted", "1 programs loaded")

            # Mock channels to return nothing, programs to return results
            async def mock_empty_channels_gen():
                return
                yield  # This line will never execute, but makes it an async generator

            mock_load_channels.return_value = mock_empty_channels_gen()
            mock_load_programs.return_value = mock_programs_gen()

            results = []
            async for result in load_epg_file_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            # Should only have program results
            assert len(results) == 1
            assert results[0].record_type == "PROGRAMS"

            # Both loaders should be called
            mock_load_channels.assert_called_once_with(mock_session, temp_epg_file, "test_source", None)
            mock_load_programs.assert_called_once_with(mock_session, temp_epg_file, "test_source", "UTC", None)

    @pytest.mark.asyncio
    async def test_load_epg_file_async_empty_results(self, mock_session, temp_epg_file):
        """Test EPG file loading with no results from either loader."""
        with patch(
            "ingest.epg_loader.load_epg_channels_async"
        ) as mock_load_channels, patch(
            "ingest.epg_loader.load_programs_async"
        ) as mock_load_programs:

            # Both loaders return empty async generators
            async def mock_empty_channels_gen():
                return
                yield  # This line will never execute, but makes it an async generator

            async def mock_empty_programs_gen():
                return
                yield  # This line will never execute, but makes it an async generator

            mock_load_channels.return_value = mock_empty_channels_gen()
            mock_load_programs.return_value = mock_empty_programs_gen()

            results = []
            async for result in load_epg_file_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            # Should have no results
            assert len(results) == 0

            # Both loaders should still be called
            mock_load_channels.assert_called_once_with(mock_session, temp_epg_file, "test_source", None)
            mock_load_programs.assert_called_once_with(mock_session, temp_epg_file, "test_source", "UTC", None)

    @pytest.mark.asyncio
    async def test_load_epg_file_async_channels_loader_error(
        self, mock_session, temp_epg_file
    ):
        """Test EPG file loading when channels loader raises an exception."""
        with patch(
            "ingest.epg_loader.load_epg_channels_async"
        ) as mock_load_channels:

            mock_load_channels.side_effect = Exception("Channels loader error")

            # Should propagate the loader exception
            with pytest.raises(Exception, match="Channels loader error"):
                async for result in load_epg_file_async(
                    mock_session, temp_epg_file, "test_source", "UTC"
                ):
                    pass

    @pytest.mark.asyncio
    async def test_load_epg_file_async_programs_loader_error(
        self, mock_session, temp_epg_file
    ):
        """Test EPG file loading when programs loader raises an exception."""
        with patch(
            "ingest.epg_loader.load_epg_channels_async"
        ) as mock_load_channels, patch(
            "ingest.epg_loader.load_programs_async"
        ) as mock_load_programs:

            # Mock successful channels loading
            async def mock_channels_gen():
                yield LoadResult(
                    "EPG_CHANNELS", "bulk", "upserted", "1 channels loaded"
                )

            mock_load_channels.return_value = mock_channels_gen()
            mock_load_programs.side_effect = Exception("Programs loader error")

            # Should get channels result, then propagate programs loader exception
            results = []
            with pytest.raises(Exception, match="Programs loader error"):
                async for result in load_epg_file_async(
                    mock_session, temp_epg_file, "test_source", "UTC"
                ):
                    results.append(result)

            # Should have gotten the channels result before the error
            assert len(results) == 1
            assert results[0].record_type == "EPG_CHANNELS"

    @pytest.mark.asyncio
    async def test_load_epg_file_async_with_task_id(self, mock_session, temp_epg_file):
        """Test EPG file loading with task_id parameter."""
        with patch(
            "ingest.epg_loader.load_epg_channels_async"
        ) as mock_load_channels, patch(
            "ingest.epg_loader.load_programs_async"
        ) as mock_load_programs:

            async def mock_channels_gen():
                yield LoadResult(
                    "EPG_CHANNELS", "bulk", "upserted", "1 channels loaded"
                )

            async def mock_programs_gen():
                yield LoadResult("PROGRAMS", "bulk", "upserted", "1 programs loaded")

            mock_load_channels.return_value = mock_channels_gen()
            mock_load_programs.return_value = mock_programs_gen()

            results = []
            async for result in load_epg_file_async(
                mock_session,
                temp_epg_file,
                "test_source",
                "UTC",
                task_id="test_task_123",
            ):
                results.append(result)

            # Should get results from both loaders
            assert len(results) == 2

            # Verify both loaders were called with task_id
            mock_load_channels.assert_called_once_with(mock_session, temp_epg_file, "test_source", "test_task_123")
            mock_load_programs.assert_called_once_with(mock_session, temp_epg_file, "test_source", "UTC", "test_task_123")

    @pytest.mark.asyncio
    async def test_load_epg_file_async_generator_behavior(self, mock_session, temp_epg_file):
        """Test that load_epg_file_async properly yields results as they come."""
        with patch(
            "ingest.epg_loader.load_epg_channels_async"
        ) as mock_load_channels, patch(
            "ingest.epg_loader.load_programs_async"
        ) as mock_load_programs:

            # Mock generators that yield multiple results
            async def mock_channels_gen():
                yield LoadResult("EPG_CHANNELS", "bulk", "upserted", "Batch 1")
                yield LoadResult("EPG_CHANNELS", "bulk", "upserted", "Batch 2")

            async def mock_programs_gen():
                yield LoadResult("PROGRAMS", "bulk", "upserted", "Program batch 1")
                yield LoadResult("PROGRAMS", "bulk", "upserted", "Program batch 2")

            mock_load_channels.return_value = mock_channels_gen()
            mock_load_programs.return_value = mock_programs_gen()

            results = []
            async for result in load_epg_file_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            # Should get all results in correct order (channels first, then programs)
            assert len(results) == 4
            assert results[0].record_type == "EPG_CHANNELS"
            assert results[0].message == "Batch 1"
            assert results[1].record_type == "EPG_CHANNELS"
            assert results[1].message == "Batch 2"
            assert results[2].record_type == "PROGRAMS"
            assert results[2].message == "Program batch 1"
            assert results[3].record_type == "PROGRAMS"
            assert results[3].message == "Program batch 2"

    @pytest.mark.asyncio
    async def test_load_epg_file_async_mixed_results(self, mock_session, temp_epg_file):
        """Test EPG file loading with mixed success/error/skip results."""
        with patch(
            "ingest.epg_loader.load_epg_channels_async"
        ) as mock_load_channels, patch(
            "ingest.epg_loader.load_programs_async"
        ) as mock_load_programs:

            # Mock mixed results
            async def mock_channels_gen():
                yield LoadResult(
                    "EPG_CHANNELS", "bulk", "upserted", "Channels loaded successfully"
                )

            async def mock_programs_gen():
                yield LoadResult(
                    "PROGRAMS", "bulk", "skipped", "No program changes detected"
                )

            mock_load_channels.return_value = mock_channels_gen()
            mock_load_programs.return_value = mock_programs_gen()

            results = []
            async for result in load_epg_file_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            # Should get both results with different statuses
            assert len(results) == 2
            assert results[0].status == "upserted"
            assert results[1].status == "skipped"

    @pytest.mark.asyncio
    async def test_load_epg_file_async_file_path_handling(self, mock_session, create_temp_epg_file):
        """Test that file path is correctly passed to both loaders."""
        # Create a specific test file
        test_file = create_temp_epg_file(
            '<?xml version="1.0"?><tv><channel id="test"><display-name>Test</display-name></channel></tv>',
            "specific_test.xml"
        )

        with patch(
            "ingest.epg_loader.load_epg_channels_async"
        ) as mock_load_channels, patch(
            "ingest.epg_loader.load_programs_async"
        ) as mock_load_programs:

            async def mock_empty_channels_gen():
                return
                yield  # This line will never execute, but makes it an async generator

            async def mock_empty_programs_gen():
                return
                yield  # This line will never execute, but makes it an async generator

            mock_load_channels.return_value = mock_empty_channels_gen()
            mock_load_programs.return_value = mock_empty_programs_gen()

            results = []
            async for result in load_epg_file_async(
                mock_session, test_file, "test_source", "UTC"
            ):
                results.append(result)

            # Verify both loaders were called with the specific file path
            mock_load_channels.assert_called_once_with(mock_session, test_file, "test_source", None)
            mock_load_programs.assert_called_once_with(mock_session, test_file, "test_source", "UTC", None)
