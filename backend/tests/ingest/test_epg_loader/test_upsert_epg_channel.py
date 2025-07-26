"""Tests for _upsert_epg_channel function following atomic design principles."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.exc import SQLAlchemyError

from ingest.epg_loader import _upsert_epg_channel, LoadResult


class TestUpsertEpgChannel:
    """Test _upsert_epg_channel function functionality."""

    def test_upsert_epg_channel_success(self, mock_session, sample_epg_channel):
        """Test successful EPG channel upsert."""
        # Mock successful execution
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = _upsert_epg_channel(mock_session, sample_epg_channel)

        # Verify database interaction
        mock_session.execute.assert_called_once()
        
        # Verify result
        assert isinstance(result, LoadResult)
        assert result.record_type == "EPG_CHANNEL"
        assert result.record_id == "test_source:channel1"
        assert result.status == "upserted"
        assert "Test Channel" in result.message

    def test_upsert_epg_channel_no_changes(self, mock_session, sample_epg_channel):
        """Test EPG channel upsert with no changes detected."""
        # Mock no changes (rowcount = 0)
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = _upsert_epg_channel(mock_session, sample_epg_channel)

        # Verify result
        assert result.status == "skipped"
        assert result.message == "No changes detected"

    def test_upsert_epg_channel_with_none_icon_url(self, mock_session):
        """Test EPG channel upsert with None icon_url."""
        from models.models import EpgChannel
        
        channel = EpgChannel(
            source="test_source",
            channel_id="channel1",
            display_name="Test Channel",
            icon_url=None
        )

        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = _upsert_epg_channel(mock_session, channel)

        assert result.status == "upserted"
        mock_session.execute.assert_called_once()

    def test_upsert_epg_channel_with_unicode_characters(self, mock_session, unicode_epg_channel):
        """Test EPG channel upsert with unicode characters."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = _upsert_epg_channel(mock_session, unicode_epg_channel)

        assert result.status == "upserted"
        assert "Tëst Chännél 中文" in result.message

    def test_upsert_epg_channel_database_error(self, mock_session, sample_epg_channel):
        """Test EPG channel upsert with database error."""
        # Mock database error
        mock_session.execute.side_effect = SQLAlchemyError("Database connection failed")

        result = _upsert_epg_channel(mock_session, sample_epg_channel)

        # Verify error handling
        assert result.status == "error"
        assert "Database connection failed" in result.message
        assert result.record_type == "EPG_CHANNEL"
        assert result.record_id == "test_source:channel1"

    def test_upsert_epg_channel_generic_exception(self, mock_session, sample_epg_channel):
        """Test EPG channel upsert with generic exception."""
        # Mock generic exception
        mock_session.execute.side_effect = Exception("Unexpected error")

        result = _upsert_epg_channel(mock_session, sample_epg_channel)

        # Verify error handling
        assert result.status == "error"
        assert "Unexpected error" in result.message

    @pytest.mark.parametrize("rowcount,expected_status", [
        (1, "upserted"),
        (2, "upserted"),  # Multiple rows affected still counts as upserted
        (0, "skipped"),
    ])
    def test_upsert_epg_channel_rowcount_variations(self, mock_session, sample_epg_channel, rowcount, expected_status):
        """Test EPG channel upsert with different rowcount values."""
        mock_result = Mock()
        mock_result.rowcount = rowcount
        mock_session.execute.return_value = mock_result

        result = _upsert_epg_channel(mock_session, sample_epg_channel)

        assert result.status == expected_status

    @patch('ingest.epg_loader.logger')
    def test_upsert_epg_channel_logging(self, mock_logger, mock_session, sample_epg_channel):
        """Test EPG channel upsert logging behavior."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        _upsert_epg_channel(mock_session, sample_epg_channel)

        # Verify debug logging was called
        mock_logger.debug.assert_called_with("Upserting EPG channel %s", "channel1")

    @patch('ingest.epg_loader.logger')
    def test_upsert_epg_channel_error_logging(self, mock_logger, mock_session, sample_epg_channel):
        """Test EPG channel upsert error logging behavior."""
        mock_session.execute.side_effect = Exception("Test error")

        _upsert_epg_channel(mock_session, sample_epg_channel)

        # Verify exception logging was called
        mock_logger.exception.assert_called_once()

    def test_upsert_epg_channel_sql_statement_structure(self, mock_session, sample_epg_channel):
        """Test that the SQL statement is constructed correctly."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        _upsert_epg_channel(mock_session, sample_epg_channel)

        # Verify execute was called with a statement
        args, kwargs = mock_session.execute.call_args
        stmt = args[0]
        
        # Verify it's an insert statement (basic structure check)
        assert hasattr(stmt, 'table')
        mock_session.execute.assert_called_once()

    def test_upsert_epg_channel_with_empty_strings(self, mock_session):
        """Test EPG channel upsert with empty string values."""
        from models.models import EpgChannel
        
        channel = EpgChannel(
            source="test_source",
            channel_id="channel1",
            display_name="",  # Empty display name
            icon_url=""  # Empty icon URL
        )

        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = _upsert_epg_channel(mock_session, channel)

        assert result.status == "upserted"
        mock_session.execute.assert_called_once()
