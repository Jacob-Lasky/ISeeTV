"""Tests for load_m3u_file_async function in M3U loader."""

import pytest
from unittest.mock import patch
from ingest.m3u_loader import load_m3u_file_async, LoadResult


class TestLoadM3uFileAsync:
    """Test cases for load_m3u_file_async function."""

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.load_m3u_channels_async")
    @patch("ingest.m3u_loader.apply_post_load_rules")
    async def test_load_m3u_file_async_success(
        self, mock_apply_rules, mock_load_channels, mock_session
    ):
        """Test successful loading of M3U file with post-load rules."""

        # Mock load_m3u_channels_async to return async generator
        async def mock_channel_generator():
            yield LoadResult(
                "M3U_CHANNEL", "test_source:channel1", "upserted", "Channel 1 loaded"
            )
            yield LoadResult(
                "M3U_CHANNEL", "test_source:channel2", "upserted", "Channel 2 loaded"
            )
            yield LoadResult(
                "M3U_CHANNEL", "test_source:channel3", "upserted", "Channel 3 loaded"
            )

        mock_load_channels.return_value = mock_channel_generator()

        # Mock post-load rules to return dict as expected by real function
        mock_apply_rules.return_value = {"processed": 3, "filtered": 1, "passed": 2}

        file_path = "/test/file.m3u"
        source_name = "test_source"
        task_id = "test_task_123"

        # Execute async generator
        results = []
        async for result in load_m3u_file_async(
            mock_session, file_path, source_name, task_id
        ):
            results.append(result)

        # Verify load_m3u_channels_async was called correctly
        mock_load_channels.assert_called_once_with(
            mock_session, file_path, source_name, task_id
        )

        # Verify post-load rules were applied
        mock_apply_rules.assert_called_once_with("m3u_channels", source_name)

        # Verify results (3 channel results + 1 rule result)
        assert len(results) == 4

        # Check channel results
        for i in range(3):
            assert results[i].record_type == "M3U_CHANNEL"
            assert results[i].record_id == f"test_source:channel{i + 1}"
            assert results[i].status == "upserted"

        # Check rule result
        assert results[3].record_type == "M3U_CHANNEL"
        assert results[3].record_id == "RULES"
        assert results[3].status == "success"

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.load_m3u_channels_async")
    @patch("ingest.m3u_loader.apply_post_load_rules")
    async def test_load_m3u_file_async_without_task_id(
        self, mock_apply_rules, mock_load_channels, mock_session
    ):
        """Test loading M3U file without task tracking."""

        # Mock load_m3u_channels_async
        async def mock_channel_generator():
            yield LoadResult(
                "M3U_CHANNEL", "test_source:channel1", "upserted", "Channel 1 loaded"
            )

        mock_load_channels.return_value = mock_channel_generator()
        mock_apply_rules.return_value = {"processed": 0, "filtered": 0, "passed": 0}

        file_path = "/test/file.m3u"
        source_name = "test_source"

        # Execute async generator without task_id
        results = []
        async for result in load_m3u_file_async(mock_session, file_path, source_name):
            results.append(result)

        # Verify load_m3u_channels_async was called without task_id
        mock_load_channels.assert_called_once_with(
            mock_session, file_path, source_name, None
        )

        # Verify results (1 channel result + 1 rule result)
        assert len(results) == 2
        assert results[0].record_type == "M3U_CHANNEL"
        assert results[1].record_type == "M3U_CHANNEL"
        assert results[1].record_id == "RULES"

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.load_m3u_channels_async")
    @patch("ingest.m3u_loader.apply_post_load_rules")
    async def test_load_m3u_file_async_empty_file(
        self, mock_apply_rules, mock_load_channels, mock_session
    ):
        """Test loading empty M3U file."""

        # Mock empty channel generator
        async def mock_empty_generator():
            return
            yield  # This line will never be reached

        mock_load_channels.return_value = mock_empty_generator()
        mock_apply_rules.return_value = {"processed": 0, "filtered": 0, "passed": 0}

        results = []
        async for result in load_m3u_file_async(
            mock_session, "/test/empty.m3u", "test_source"
        ):
            results.append(result)

        # Verify no channel results but post-load rules still applied
        assert len(results) == 1
        assert results[0].record_type == "M3U_CHANNEL"
        assert results[0].record_id == "RULES"
        mock_apply_rules.assert_called_once()

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.load_m3u_channels_async")
    @patch("ingest.m3u_loader.apply_post_load_rules")
    async def test_load_m3u_file_async_channel_loading_error(
        self, mock_apply_rules, mock_load_channels, mock_session
    ):
        """Test handling of channel loading errors."""

        # Mock channel generator with error
        async def mock_error_generator():
            yield LoadResult(
                "M3U_CHANNEL", "test_source:channel1", "upserted", "Channel 1 loaded"
            )
            yield LoadResult("M3U_CHANNEL", "BATCH", "error", "Database error occurred")

        mock_load_channels.return_value = mock_error_generator()
        mock_apply_rules.return_value = {"processed": 0, "filtered": 0, "passed": 0}

        results = []
        async for result in load_m3u_file_async(
            mock_session, "/test/file.m3u", "test_source"
        ):
            results.append(result)

        # Verify both success and error results are yielded
        assert len(results) == 3
        assert results[0].status == "upserted"
        assert results[1].status == "error"
        assert results[2].record_type == "M3U_CHANNEL"
        assert results[2].record_id == "RULES"

        # Post-load rules should still be applied even after errors
        mock_apply_rules.assert_called_once()

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.load_m3u_channels_async")
    @patch("ingest.m3u_loader.apply_post_load_rules")
    async def test_load_m3u_file_async_post_load_rules_error(
        self, mock_apply_rules, mock_load_channels, mock_session
    ):
        """Test handling of post-load rules errors."""

        # Mock successful channel loading
        async def mock_channel_generator():
            yield LoadResult(
                "M3U_CHANNEL", "test_source:channel1", "upserted", "Channel 1 loaded"
            )

        mock_load_channels.return_value = mock_channel_generator()

        # Mock post-load rules error
        mock_apply_rules.side_effect = Exception("Post-load rules failed")

        results = []
        async for result in load_m3u_file_async(
            mock_session, "/test/file.m3u", "test_source"
        ):
            results.append(result)

        # Verify channel result and error result
        assert len(results) == 2
        assert results[0].status == "upserted"  # Channel result
        assert results[1].record_type == "M3U_CHANNEL"
        assert results[1].record_id == "RULES"
        assert results[1].status == "error"
        assert "Post-load rules failed" in results[1].message

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.load_m3u_channels_async")
    @patch("ingest.m3u_loader.apply_post_load_rules")
    async def test_load_m3u_file_async_no_post_load_rules(
        self, mock_apply_rules, mock_load_channels, mock_session
    ):
        """Test loading when no post-load rules are configured."""

        # Mock channel loading
        async def mock_channel_generator():
            yield LoadResult(
                "M3U_CHANNEL", "test_source:channel1", "upserted", "Channel 1 loaded"
            )
            yield LoadResult(
                "M3U_CHANNEL", "test_source:channel2", "upserted", "Channel 2 loaded"
            )

        mock_load_channels.return_value = mock_channel_generator()

        # Mock no post-load rules
        mock_apply_rules.return_value = {"processed": 0, "filtered": 0, "passed": 0}

        results = []
        async for result in load_m3u_file_async(
            mock_session, "/test/file.m3u", "test_source"
        ):
            results.append(result)

        # Verify channel results + rule result (3 total: 2 channels + 1 rule)
        assert len(results) == 3
        assert results[0].record_type == "M3U_CHANNEL"
        assert results[1].record_type == "M3U_CHANNEL"
        assert results[2].record_type == "M3U_CHANNEL"
        assert results[2].record_id == "RULES"

        # Verify post-load rules were still attempted
        mock_apply_rules.assert_called_once()

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.load_m3u_channels_async")
    @patch("ingest.m3u_loader.apply_post_load_rules")
    async def test_load_m3u_file_async_large_file_processing(
        self, mock_apply_rules, mock_load_channels, mock_session
    ):
        """Test loading large M3U file with many channels."""

        # Mock large channel generator (1000 channels)
        async def mock_large_generator():
            for i in range(1000):
                yield LoadResult(
                    "M3U_CHANNEL",
                    f"test_source:channel{i:04d}",
                    "upserted",
                    f"Channel {i} loaded",
                )

        mock_load_channels.return_value = mock_large_generator()
        mock_apply_rules.return_value = {"processed": 1, "filtered": 0, "passed": 1}

        results = []
        async for result in load_m3u_file_async(
            mock_session, "/test/large_file.m3u", "test_source", "large_task"
        ):
            results.append(result)

        # Verify all results (1000 channels + 1 rule)
        assert len(results) == 1001

        # Verify channel results
        for i in range(1000):
            assert results[i].record_type == "M3U_CHANNEL"
            assert results[i].record_id == f"test_source:channel{i:04d}"
            assert results[i].status == "upserted"

        # Verify rule result
        assert results[1000].record_type == "M3U_CHANNEL"
        assert results[1000].record_id == "RULES"
        assert results[1000].status == "success"

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.load_m3u_channels_async")
    @patch("ingest.m3u_loader.apply_post_load_rules")
    async def test_load_m3u_file_async_unicode_source_name(
        self, mock_apply_rules, mock_load_channels, mock_session
    ):
        """Test loading M3U file with unicode source name."""

        # Mock channel loading
        async def mock_channel_generator():
            yield LoadResult(
                "M3U_CHANNEL", "测试源:channel1", "upserted", "Unicode channel loaded"
            )

        mock_load_channels.return_value = mock_channel_generator()
        mock_apply_rules.return_value = {"processed": 0, "filtered": 0, "passed": 0}

        unicode_source = "测试源"  # Chinese characters

        results = []
        async for result in load_m3u_file_async(
            mock_session, "/test/unicode.m3u", unicode_source
        ):
            results.append(result)

        # Verify unicode source was handled correctly
        mock_load_channels.assert_called_once_with(
            mock_session, "/test/unicode.m3u", unicode_source, None
        )
        mock_apply_rules.assert_called_once_with("m3u_channels", unicode_source)

        assert len(results) == 2
        assert results[0].record_id == "测试源:channel1"
        assert results[1].record_type == "M3U_CHANNEL"
        assert results[1].record_id == "RULES"

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.load_m3u_channels_async")
    @patch("ingest.m3u_loader.apply_post_load_rules")
    async def test_load_m3u_file_async_mixed_results(
        self, mock_apply_rules, mock_load_channels, mock_session
    ):
        """Test loading with mixed success/error results from channels."""

        # Mock channel generator with mixed results
        async def mock_mixed_generator():
            yield LoadResult(
                "M3U_CHANNEL", "test_source:channel1", "upserted", "Channel 1 loaded"
            )
            yield LoadResult(
                "M3U_CHANNEL",
                "test_source:channel2",
                "error",
                "Channel 2 failed validation",
            )
            yield LoadResult(
                "M3U_CHANNEL", "test_source:channel3", "upserted", "Channel 3 loaded"
            )
            yield LoadResult(
                "M3U_CHANNEL", "BATCH", "error", "Database connection lost"
            )

        mock_load_channels.return_value = mock_mixed_generator()
        mock_apply_rules.return_value = {"processed": 3, "filtered": 1, "passed": 2}

        results = []
        async for result in load_m3u_file_async(
            mock_session, "/test/file.m3u", "test_source"
        ):
            results.append(result)

        # Verify all results are yielded (4 channel results + 1 rule result)
        assert len(results) == 5

        # Check mixed statuses
        statuses = [result.status for result in results[:4]]  # Channel results
        assert "upserted" in statuses
        assert "error" in statuses

        # Check rule result
        assert results[4].record_type == "M3U_CHANNEL"
        assert results[4].record_id == "RULES"
        assert results[4].status == "success"

    @pytest.mark.asyncio
    @patch("ingest.m3u_loader.load_m3u_channels_async")
    @patch("ingest.m3u_loader.apply_post_load_rules")
    async def test_load_m3u_file_async_long_file_path(
        self, mock_apply_rules, mock_load_channels, mock_session
    ):
        """Test loading M3U file with very long file path."""
        # Create very long file path
        long_path = "/very/long/path/" + "directory/" * 50 + "file.m3u"

        # Mock channel loading
        async def mock_channel_generator():
            yield LoadResult(
                "M3U_CHANNEL", "test_source:channel1", "upserted", "Channel loaded"
            )

        mock_load_channels.return_value = mock_channel_generator()
        mock_apply_rules.return_value = {"processed": 0, "filtered": 0, "passed": 0}

        results = []
        async for result in load_m3u_file_async(mock_session, long_path, "test_source"):
            results.append(result)

        # Verify long path was handled correctly
        mock_load_channels.assert_called_once_with(
            mock_session, long_path, "test_source", None
        )
        assert len(results) == 2
        assert results[0].record_type == "M3U_CHANNEL"
        assert results[1].record_type == "M3U_CHANNEL"
        assert results[1].record_id == "RULES"
