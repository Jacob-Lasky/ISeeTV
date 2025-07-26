"""Tests for _upsert_program function following atomic design principles."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone

from ingest.epg_loader import _upsert_program, LoadResult


class TestUpsertProgram:
    """Test _upsert_program function functionality."""

    def test_upsert_program_success(self, mock_session, sample_program):
        """Test successful program upsert."""
        # Mock successful execution
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = _upsert_program(mock_session, sample_program)

        # Verify database interaction
        mock_session.execute.assert_called_once()
        
        # Verify result
        assert isinstance(result, LoadResult)
        assert result.record_type == "PROGRAM"
        assert result.record_id == "test_source:prog1"
        assert result.status == "upserted"
        assert "Test Program" in result.message
        assert "channel1" in result.message

    def test_upsert_program_no_changes(self, mock_session, sample_program):
        """Test program upsert with no changes detected."""
        # Mock no changes (rowcount = 0)
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = _upsert_program(mock_session, sample_program)

        # Verify result
        assert result.status == "skipped"
        assert result.message == "No changes detected"

    def test_upsert_program_with_none_description(self, mock_session):
        """Test program upsert with None description."""
        from models.models import Program
        
        program = Program(
            source="test_source",
            program_id="prog1",
            channel_id="channel1",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            title="Test Program",
            description=None
        )

        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = _upsert_program(mock_session, program)

        assert result.status == "upserted"
        mock_session.execute.assert_called_once()

    def test_upsert_program_with_unicode_characters(self, mock_session, unicode_program):
        """Test program upsert with unicode characters."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = _upsert_program(mock_session, unicode_program)

        assert result.status == "upserted"
        assert "Tëst Prögräm 中文" in result.message

    def test_upsert_program_database_error(self, mock_session, sample_program):
        """Test program upsert with database error."""
        # Mock database error
        mock_session.execute.side_effect = SQLAlchemyError("Database connection failed")

        result = _upsert_program(mock_session, sample_program)

        # Verify error handling
        assert result.status == "error"
        assert "Database connection failed" in result.message
        assert result.record_type == "PROGRAM"
        assert result.record_id == "test_source:prog1"

    def test_upsert_program_generic_exception(self, mock_session, sample_program):
        """Test program upsert with generic exception."""
        # Mock generic exception
        mock_session.execute.side_effect = Exception("Unexpected error")

        result = _upsert_program(mock_session, sample_program)

        # Verify error handling
        assert result.status == "error"
        assert "Unexpected error" in result.message

    @pytest.mark.parametrize("rowcount,expected_status", [
        (1, "upserted"),
        (2, "upserted"),  # Multiple rows affected still counts as upserted
        (0, "skipped"),
    ])
    def test_upsert_program_rowcount_variations(self, mock_session, sample_program, rowcount, expected_status):
        """Test program upsert with different rowcount values."""
        mock_result = Mock()
        mock_result.rowcount = rowcount
        mock_session.execute.return_value = mock_result

        result = _upsert_program(mock_session, sample_program)

        assert result.status == expected_status

    @patch('ingest.epg_loader.logger')
    def test_upsert_program_logging(self, mock_logger, mock_session, sample_program):
        """Test program upsert logging behavior."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        _upsert_program(mock_session, sample_program)

        # Verify debug logging was called
        mock_logger.debug.assert_called_with("Upserting program %s", "prog1")

    @patch('ingest.epg_loader.logger')
    def test_upsert_program_error_logging(self, mock_logger, mock_session, sample_program):
        """Test program upsert error logging behavior."""
        mock_session.execute.side_effect = Exception("Test error")

        _upsert_program(mock_session, sample_program)

        # Verify exception logging was called
        mock_logger.exception.assert_called_with("Error upserting program %s: %s", "prog1", mock_session.execute.side_effect)

    def test_upsert_program_sql_statement_structure(self, mock_session, sample_program):
        """Test that the SQL statement is constructed correctly."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        _upsert_program(mock_session, sample_program)

        # Verify execute was called with a statement
        args, kwargs = mock_session.execute.call_args
        stmt = args[0]
        
        # Verify it's an insert statement (basic structure check)
        assert hasattr(stmt, 'table')
        mock_session.execute.assert_called_once()

    def test_upsert_program_with_empty_strings(self, mock_session):
        """Test program upsert with empty string values."""
        from models.models import Program
        
        program = Program(
            source="test_source",
            program_id="prog1",
            channel_id="channel1",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            title="",  # Empty title
            description=""  # Empty description
        )

        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = _upsert_program(mock_session, program)

        assert result.status == "upserted"
        mock_session.execute.assert_called_once()

    def test_upsert_program_with_long_strings(self, mock_session):
        """Test program upsert with very long strings."""
        from models.models import Program
        
        long_title = "A" * 1000
        long_description = "B" * 5000
        
        program = Program(
            source="test_source",
            program_id="prog1",
            channel_id="channel1",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            title=long_title,
            description=long_description
        )

        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = _upsert_program(mock_session, program)

        assert result.status == "upserted"
        assert long_title in result.message

    def test_upsert_program_with_timezone_aware_datetime(self, mock_session):
        """Test program upsert with timezone-aware datetime objects."""
        from models.models import Program
        
        # Test with different timezone
        start_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)
        
        program = Program(
            source="test_source",
            program_id="prog1",
            channel_id="channel1",
            start_time=start_time,
            end_time=end_time,
            title="Test Program",
            description="Test description"
        )

        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = _upsert_program(mock_session, program)

        assert result.status == "upserted"
        mock_session.execute.assert_called_once()

    def test_upsert_program_with_special_characters_in_ids(self, mock_session):
        """Test program upsert with special characters in IDs."""
        from models.models import Program
        
        program = Program(
            source="test-source_123",
            program_id="prog:1@test.com",
            channel_id="channel-1_test",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            title="Test Program",
            description="Test description"
        )

        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = _upsert_program(mock_session, program)

        assert result.status == "upserted"
        assert result.record_id == "test-source_123:prog:1@test.com"
