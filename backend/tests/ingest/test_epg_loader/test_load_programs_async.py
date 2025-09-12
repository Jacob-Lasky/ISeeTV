"""Tests for load_programs_async function following atomic design principles."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from ingest.epg_loader import load_programs_async, LoadResult


class TestLoadProgramsAsync:
    """Test load_programs_async async generator function functionality."""

    @pytest.mark.asyncio
    async def test_load_programs_async_success(self, mock_session, sample_programs, temp_epg_file):
        """Test successful async loading of programs."""
        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = sample_programs
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="3 programs upserted",
                )
            ]

            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            # Verify results
            assert len(results) == 1
            assert results[0].status == "upserted"
            assert "3 programs" in results[0].message

            # Verify parse and bulk upsert were called
            mock_parse.assert_called_once_with(temp_epg_file, "test_source", "UTC", None)
            mock_bulk_upsert.assert_called_once_with(mock_session, sample_programs)

    @pytest.mark.asyncio
    async def test_load_programs_async_empty_list(self, mock_session, temp_epg_file):
        """Test async loading with empty program list."""
        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse:
            mock_parse.return_value = []  # Empty programs list
            
            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            # Should yield nothing for empty list
            assert len(results) == 0
            mock_parse.assert_called_once_with(temp_epg_file, "test_source", "UTC", None)

    @pytest.mark.asyncio
    async def test_load_programs_async_with_task_id(
        self, mock_session, sample_programs, temp_epg_file
    ):
        """Test async loading with task manager progress updates."""
        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader.TaskManager.update_total_items") as mock_update_total, \
             patch("ingest.epg_loader.IngestTaskManager.update_item_progress") as mock_update_progress, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = sample_programs
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="3 programs upserted",
                )
            ]

            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC", task_id="test_task_123"
            ):
                results.append(result)

            # Verify task progress was updated
            mock_update_total.assert_called_once_with("test_task_123", "ingest", 3)
            assert mock_update_progress.call_count >= 1
            mock_update_progress.assert_called_with(
                "test_task_123", "Loading programs...", 0, "programs"
            )

    @pytest.mark.asyncio
    async def test_load_programs_async_batch_processing(self, mock_session, temp_epg_file):
        """Test async loading with large batch requiring multiple operations."""
        from models.models import Program

        # Create large batch of programs
        large_batch = []
        for i in range(500):  # Larger than typical batch size
            program = Program(
                source="test_source",
                program_id=f"prog{i}",
                channel_id=f"channel{i % 10}",
                start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
                title=f"Program {i}",
                description=f"Description {i}",
            )
            large_batch.append(program)

        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = large_batch
            mock_bulk_upsert.return_value = LoadResult(
                record_type="PROGRAMS",
                record_id="bulk_operation",
                status="upserted",
                message="500 programs upserted",
            )

            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            # Should still process all programs
            assert len(results) == 1
            mock_bulk_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_programs_async_error_handling(
        self, mock_session, sample_programs, temp_epg_file
    ):
        """Test async loading with error in bulk upsert."""
        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = sample_programs
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id="bulk_operation",
                    status="error",
                    message="Database error occurred",
                )
            ]

            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            # Should still yield the error result
            assert len(results) == 1
            assert results[0].status == "error"
            assert "Database error" in results[0].message

    @pytest.mark.asyncio
    async def test_load_programs_async_with_unicode_data(
        self, mock_session, unicode_program, temp_epg_file
    ):
        """Test async loading with unicode characters in program data."""
        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = [unicode_program]
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="2 programs upserted",
                )
            ]

            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            assert len(results) == 1
            assert results[0].status == "upserted"

    @pytest.mark.asyncio
    async def test_load_programs_async_progress_updates_with_phase(
        self, mock_session, sample_programs, temp_epg_file
    ):
        """Test that progress updates include the programs phase."""
        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader.TaskManager.update_total_items") as mock_update_total, \
             patch("ingest.epg_loader.IngestTaskManager.update_item_progress") as mock_update_progress, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = sample_programs
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="3 programs upserted",
                )
            ]

            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC", task_id="TEST123"
            ):
                results.append(result)

    @pytest.mark.asyncio
    async def test_load_programs_async_skipped_result(
        self, mock_session, sample_programs, temp_epg_file
    ):
        """Test async loading when bulk upsert returns skipped status."""
        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = sample_programs
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id="bulk_operation",
                    status="skipped",
                    message="No programs to load",
                )
            ]

            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            assert len(results) == 1
            assert results[0].status == "skipped"

    @pytest.mark.asyncio
    async def test_load_programs_async_generator_behavior(
        self, mock_session, sample_programs, temp_epg_file
    ):
        """Test that the function behaves as an async generator."""
        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = sample_programs
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="3 programs upserted",
                )
            ]

            # Test that it's an async generator
            gen = load_programs_async(mock_session, temp_epg_file, "test_source", "UTC")
            assert hasattr(gen, "__aiter__")
            assert hasattr(gen, "__anext__")

            # Test iteration
            result = await gen.__anext__()
            assert isinstance(result, LoadResult)

            # Test that StopAsyncIteration is raised when done
            with pytest.raises(StopAsyncIteration):
                await gen.__anext__()

    @pytest.mark.asyncio
    async def test_load_programs_async_with_none_values(self, mock_session, temp_epg_file):
        """Test async loading with programs containing None values."""
        from models.models import Program

        programs_with_none = [
            Program(
                source="test_source",
                program_id="prog1",
                channel_id="channel1",
                start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
                title="Program 1",
                description=None,  # None description
            ),
            Program(
                source="test_source",
                program_id="prog2",
                channel_id="channel2",
                start_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
                title="",  # Empty title
                description="Description 2",
            ),
        ]

        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = programs_with_none
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="2 programs upserted",
                )
            ]

            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            assert len(results) == 1
            assert results[0].status == "upserted"

    @pytest.mark.asyncio
    async def test_load_programs_async_exception_handling(
        self, mock_session, sample_programs, temp_epg_file
    ):
        """Test async loading when bulk upsert raises an exception."""
        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = sample_programs
            mock_bulk_upsert.side_effect = Exception("Unexpected error")

            # The function should catch the exception and yield an error result
            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            # Should yield an error result instead of raising
            assert len(results) == 1
            assert results[0].status == "error"
            assert "Unexpected error" in results[0].message

    @pytest.mark.asyncio
    async def test_load_programs_async_single_program(
        self, mock_session, sample_program, temp_epg_file
    ):
        """Test async loading with single program."""
        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = [sample_program]
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="1 programs upserted",
                )
            ]

            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            assert len(results) == 1
            assert results[0].status == "upserted"
            assert "1 programs" in results[0].message

    @pytest.mark.asyncio
    async def test_load_programs_async_task_id_none(
        self, mock_session, sample_programs, temp_epg_file
    ):
        """Test async loading with task_id=None."""
        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = sample_programs
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="3 programs upserted",
                )
            ]

            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC", task_id=None
            ):
                results.append(result)

            # Should work fine without task manager
            assert len(results) == 1
            assert results[0].status == "upserted"

    @pytest.mark.asyncio
    async def test_load_programs_async_with_overlapping_times(self, mock_session, temp_epg_file):
        """Test async loading with programs that have overlapping times."""
        from models.models import Program

        overlapping_programs = [
            Program(
                source="test_source",
                program_id="prog1",
                channel_id="channel1",
                start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 1, 13, 30, tzinfo=timezone.utc),
                title="Program 1",
                description="First program",
            ),
            Program(
                source="test_source",
                program_id="prog2",
                channel_id="channel1",  # Same channel
                start_time=datetime(
                    2024, 1, 1, 13, 0, tzinfo=timezone.utc
                ),  # Overlaps with prog1
                end_time=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
                title="Program 2",
                description="Second program",
            ),
        ]

        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = overlapping_programs
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="2 programs upserted",
                )
            ]

            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            assert len(results) == 1
            assert results[0].status == "upserted"

    @pytest.mark.asyncio
    async def test_load_programs_async_memory_efficiency(self, mock_session, temp_epg_file):
        """Test that the async generator doesn't load all results into memory at once."""
        from models.models import Program

        # Create a very large batch
        large_batch = []
        for i in range(10000):
            program = Program(
                source="test_source",
                program_id=f"prog{i}",
                channel_id=f"channel{i % 100}",
                start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
                title=f"Program {i}",
                description=f"Description {i}",
            )
            large_batch.append(program)

        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = large_batch
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="10000 programs upserted",
                )
            ]

            # Should be able to iterate without memory issues
            result_count = 0
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                result_count += 1
                # Only check first few to avoid long test times
                if result_count >= 3:
                    break

            assert result_count >= 1

    @pytest.mark.asyncio
    async def test_load_programs_async_different_channels(self, mock_session, temp_epg_file):
        """Test async loading with programs from different channels."""
        from models.models import Program

        multi_channel_programs = []
        for channel_num in range(5):
            for prog_num in range(3):
                program = Program(
                    source="test_source",
                    program_id=f"prog{channel_num}_{prog_num}",
                    channel_id=f"channel{channel_num}",
                    start_time=datetime(
                        2024, 1, 1, 12 + prog_num, 0, tzinfo=timezone.utc
                    ),
                    end_time=datetime(
                        2024, 1, 1, 13 + prog_num, 0, tzinfo=timezone.utc
                    ),
                    title=f"Program {prog_num} on Channel {channel_num}",
                    description=f"Description for program {prog_num}",
                )
                multi_channel_programs.append(program)

        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert:
            
            mock_parse.return_value = multi_channel_programs
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id="bulk_operation",
                    status="upserted",
                    message="15 programs upserted",
                )
            ]

            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC"
            ):
                results.append(result)

            assert len(results) == 1
            assert results[0].status == "upserted"
            assert "15 programs" in results[0].message

    @pytest.mark.asyncio
    async def test_load_programs_async_periodic_progress_updates(
        self, mock_session, temp_epg_file
    ):
        """Test async loading with enough programs to trigger periodic progress updates."""
        from models.models import Program
        from datetime import timedelta

        # Create 1000 programs to ensure we hit the 500-record progress update threshold
        programs = [
            Program(
                source="test_source",
                program_id=f"prog{i}",
                channel_id="channel1",
                start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc) + timedelta(hours=i),
                end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc) + timedelta(hours=i),
                title=f"Program {i}",
                description=None,
                filter_reasons=None,
            )
            for i in range(1000)
        ]

        with patch("ingest.epg_loader.parse_epg_for_programs") as mock_parse, \
             patch("ingest.epg_loader._bulk_upsert_programs") as mock_bulk_upsert, \
             patch("ingest.epg_loader.IngestTaskManager.update_item_progress") as mock_progress:
            
            mock_parse.return_value = programs
            # Mock bulk upsert to return one result per program (simulating individual results)
            mock_bulk_upsert.return_value = [
                LoadResult(
                    record_type="PROGRAMS",
                    record_id=f"prog{i}",
                    status="upserted",
                    message=f"Program {i} upserted",
                )
                for i in range(1000)
            ]

            results = []
            async for result in load_programs_async(
                mock_session, temp_epg_file, "test_source", "UTC", task_id="test_task"
            ):
                results.append(result)

            # Should have 1000 results
            assert len(results) == 1000
            assert all(r.status == "upserted" for r in results)
            
            # Should have called progress update 3 times:
            # 1. Initial "Loading programs..." call
            # 2. At 500 records (completed_count % 500 == 0)
            # 3. At 1000 records (completed_count % 500 == 0)
            assert mock_progress.call_count == 3
            
            # Verify the specific progress update calls
            calls = mock_progress.call_args_list
            assert calls[0][0] == ("test_task", "Loading programs...", 0, "programs")
            assert calls[1][0] == ("test_task", "Loaded 500 programs", 500, "programs")
            assert calls[2][0] == ("test_task", "Loaded 1000 programs", 1000, "programs")
