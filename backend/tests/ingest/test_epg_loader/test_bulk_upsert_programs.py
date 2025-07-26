"""Tests for _bulk_upsert_programs function following atomic design principles."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone

from ingest.epg_loader import _bulk_upsert_programs, LoadResult


class TestBulkUpsertPrograms:
    """Test _bulk_upsert_programs async function functionality."""

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_success_multiple(
        self, mock_session, sample_programs
    ):
        """Test successful bulk upsert of multiple programs."""
        # Mock successful execution
        mock_result = Mock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        result = await _bulk_upsert_programs(mock_session, sample_programs)

        # Verify database interaction
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 3
        assert isinstance(result[0], LoadResult)
        assert result[0].record_type == "PROGRAM"
        assert result[0].record_id == "test_source:prog1"
        assert result[0].status == "upserted"
        assert "Program 'Test Program 1' on channel1 processed" in result[0].message

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_success_single(
        self, mock_session, sample_program
    ):
        """Test successful bulk upsert of single program."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await _bulk_upsert_programs(mock_session, [sample_program])

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], LoadResult)
        row = result[0]

        assert row.status == "upserted"
        assert "Program 'Test Program' on channel1 processed" in row.message

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_empty_list(self, mock_session):
        """Test bulk upsert with empty program list."""
        result = await _bulk_upsert_programs(mock_session, [])

        # Verify no database operations
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

        # Verify empty result list
        assert result == []

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_no_changes(self, mock_session, sample_programs):
        """Test bulk upsert with no changes detected."""
        # Mock no changes (rowcount = 0)
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await _bulk_upsert_programs(mock_session, sample_programs)
        row = result[0]

        assert row.status == "skipped"
        assert "no changes detected" in row.message
        assert row.record_type == "PROGRAM"

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_with_unicode(
        self, mock_session, unicode_program
    ):
        """Test bulk upsert with unicode characters."""
        mock_result = Mock()
        mock_result.rowcount = 2
        mock_session.execute.return_value = mock_result

        result = await _bulk_upsert_programs(
            mock_session, [unicode_program, unicode_program]
        )
        row = result[0]

        assert row.status == "upserted"
        assert "Tëst Prögräm 中文" in row.message

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_database_error(
        self, mock_session, sample_programs
    ):
        """Test bulk upsert with database error."""
        # Mock database error
        mock_session.execute.side_effect = SQLAlchemyError("Database connection failed")

        result = await _bulk_upsert_programs(mock_session, sample_programs)
        row = result[0]

        # Verify error handling and rollback
        mock_session.rollback.assert_called_once()
        assert row.status == "error"
        assert "Database connection failed" in row.message

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_commit_error(
        self, mock_session, sample_programs
    ):
        """Test bulk upsert with commit error."""
        # Mock successful execute but failed commit
        mock_result = Mock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result
        mock_session.commit.side_effect = SQLAlchemyError("Commit failed")

        result = await _bulk_upsert_programs(mock_session, sample_programs)
        row = result[0]

        # Verify rollback was called
        mock_session.rollback.assert_called_once()
        assert row.status == "error"
        assert "Commit failed" in row.message

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_generic_exception(
        self, mock_session, sample_programs
    ):
        """Test bulk upsert with generic exception."""
        # Mock generic exception
        mock_session.execute.side_effect = Exception("Unexpected error")

        result = await _bulk_upsert_programs(mock_session, sample_programs)
        row = result[0]

        # Verify error handling
        mock_session.rollback.assert_called_once()
        assert row.status == "error"
        assert "Unexpected error" in row.message

    @pytest.mark.parametrize(
        "rowcount,expected_status",
        [
            (1, "upserted"),
            (5, "upserted"),
            (100, "upserted"),
            (0, "skipped"),
        ],
    )
    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_rowcount_variations(
        self, mock_session, sample_programs, rowcount, expected_status
    ):
        """Test bulk upsert with different rowcount values."""
        mock_result = Mock()
        mock_result.rowcount = rowcount
        mock_session.execute.return_value = mock_result

        result = await _bulk_upsert_programs(mock_session, sample_programs)

        # All records should have the same status based on aggregate rowcount
        assert len(result) == len(sample_programs)
        for row in result:
            assert row.status == expected_status

        # Verify message content matches status
        if expected_status == "upserted":
            assert "processed" in result[0].message
        else:  # skipped
            assert "no changes detected" in result[0].message

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_data_structure(
        self, mock_session, sample_programs
    ):
        """Test that the correct data structure is passed to execute."""
        mock_result = Mock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        await _bulk_upsert_programs(mock_session, sample_programs)

        # Verify execute was called with correct parameters
        args, kwargs = mock_session.execute.call_args
        stmt = args[0]
        data_list = args[1] if len(args) > 1 else kwargs.get("parameters", [])

        # Verify it's a bulk insert statement
        assert hasattr(stmt, "table")

        # Verify data structure (should be list of dicts)
        assert isinstance(data_list, list)
        assert isinstance(data_list[0], dict)

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_large_batch(self, mock_session):
        """Test bulk upsert with large batch of programs."""
        from models.models import Program

        # Create large batch of programs
        large_batch = []
        for i in range(1000):
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

        mock_result = Mock()
        mock_result.rowcount = 1000
        mock_session.execute.return_value = mock_result

        result = await _bulk_upsert_programs(mock_session, large_batch)

        assert len(result) == 1000

        row = result[0]
        assert row.status == "upserted"
        assert "Program 0" in row.message

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_mixed_data_types(self, mock_session):
        """Test bulk upsert with mixed data types and edge cases."""
        from models.models import Program

        programs = [
            # Program with None description
            Program(
                source="test_source",
                program_id="prog1",
                channel_id="channel1",
                start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
                title="Program 1",
                description=None,
            ),
            # Program with empty strings
            Program(
                source="test_source",
                program_id="prog2",
                channel_id="channel2",
                start_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
                title="",
                description="",
            ),
            # Program with unicode
            Program(
                source="test_source",
                program_id="prog3",
                channel_id="channel3",
                start_time=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
                title="Tëst Prögräm 中文",
                description="Dëscriptïön 中文",
            ),
        ]

        mock_result = Mock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        result = await _bulk_upsert_programs(mock_session, programs)

        assert len(result) == 3

        row = result[0]
        assert row.status == "upserted"
        assert "Program 1" in row.message

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_transaction_rollback(
        self, mock_session, sample_programs
    ):
        """Test that transaction is properly rolled back on error."""
        # Mock execute success but commit failure
        mock_result = Mock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result
        mock_session.commit.side_effect = SQLAlchemyError("Transaction failed")

        result = await _bulk_upsert_programs(mock_session, sample_programs)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()
        row = result[0]
        assert row.status == "error"

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_with_special_characters(self, mock_session):
        """Test bulk upsert with special characters in program data."""
        from models.models import Program

        programs = [
            Program(
                source="test-source_123",
                program_id="prog:1@test.com",
                channel_id="channel-1_test",
                start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
                title="Program with special chars: !@#$%^&*()",
                description="Description with quotes 'single' \"double\" and newlines\n\r",
            )
        ]

        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await _bulk_upsert_programs(mock_session, programs)

        row = result[0]
        assert row.status == "upserted"
        assert "Program with special chars" in row.message

    @pytest.mark.asyncio
    async def test_bulk_upsert_programs_session_state_preservation(
        self, mock_session, sample_programs
    ):
        """Test that session state is preserved correctly during bulk operations."""
        mock_result = Mock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        # Track session method calls
        initial_call_count = mock_session.execute.call_count

        await _bulk_upsert_programs(mock_session, sample_programs)

        # Verify session methods were called in correct order
        assert mock_session.execute.call_count == initial_call_count + 1
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()
