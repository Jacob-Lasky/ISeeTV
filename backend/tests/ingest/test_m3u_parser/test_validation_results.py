"""Tests for M3uValidationResults class following atomic design principles.

This module focuses exclusively on testing validation results tracking logic.
Each test validates one specific aspect of validation result management.
"""

import pytest

from ingest.m3u_parser import M3uValidationResults


class TestM3uValidationResults:
    """Atomic tests for M3uValidationResults class."""

    def test_validation_results_initialization(self):
        """M3uValidationResults should initialize with empty defaultdicts and list."""
        results = M3uValidationResults()

        assert len(results.unhandled_tags) == 0
        assert len(results.unhandled_extinf_keys) == 0
        assert results.channels_without_urls == []

    def test_add_unhandled_tag(self):
        """Adding unhandled tags should increment count in defaultdict."""
        results = M3uValidationResults()

        results.unhandled_tags["EXT-X-VERSION"] += 1
        results.unhandled_tags["EXT-X-STREAM-INF"] += 1
        results.unhandled_tags["EXT-X-VERSION"] += 1  # Increment again

        assert len(results.unhandled_tags) == 2
        assert results.unhandled_tags["EXT-X-VERSION"] == 2
        assert results.unhandled_tags["EXT-X-STREAM-INF"] == 1

    def test_add_unhandled_extinf_key(self):
        """Adding unhandled EXTINF keys should increment count in defaultdict."""
        results = M3uValidationResults()

        results.unhandled_extinf_keys["custom-attr"] += 1
        results.unhandled_extinf_keys["unknown-key"] += 1
        results.unhandled_extinf_keys["custom-attr"] += 1  # Increment again

        assert len(results.unhandled_extinf_keys) == 2
        assert results.unhandled_extinf_keys["custom-attr"] == 2
        assert results.unhandled_extinf_keys["unknown-key"] == 1

    def test_add_channels_without_urls(self):
        """Channels without URLs should be tracked in list."""
        results = M3uValidationResults()

        results.channels_without_urls.append("Channel 1")
        results.channels_without_urls.append("Channel 2")
        results.channels_without_urls.append("Channel 1")  # Duplicate allowed

        assert len(results.channels_without_urls) == 3
        assert "Channel 1" in results.channels_without_urls
        assert "Channel 2" in results.channels_without_urls

    def test_validation_results_comprehensive_tracking(self):
        """Validation results should track all types of issues."""
        results = M3uValidationResults()

        # Add various unhandled tags with counts
        results.unhandled_tags["EXT-X-VERSION"] = 3
        results.unhandled_tags["EXT-X-STREAM-INF"] = 1
        results.unhandled_tags["EXT-X-MEDIA"] = 2
        results.unhandled_tags["EXTGRP"] = 5

        # Add various unhandled EXTINF keys with counts
        results.unhandled_extinf_keys["custom-attr"] = 2
        results.unhandled_extinf_keys["proprietary-key"] = 1
        results.unhandled_extinf_keys["vendor-specific"] = 3

        # Track channels without URLs
        results.channels_without_urls = ["Channel A", "Channel B", "Channel C"]

        assert len(results.unhandled_tags) == 4
        assert len(results.unhandled_extinf_keys) == 3
        assert len(results.channels_without_urls) == 3
        assert results.unhandled_tags["EXT-X-VERSION"] == 3
        assert results.unhandled_extinf_keys["custom-attr"] == 2

    def test_validation_results_defaultdict_behavior(self):
        """Validation results should use defaultdict behavior for auto-initialization."""
        results = M3uValidationResults()

        # Accessing non-existent keys should return 0 (default int value)
        assert results.unhandled_tags["NON_EXISTENT"] == 0
        assert results.unhandled_extinf_keys["NON_EXISTENT"] == 0

        # After accessing, they should exist with value 0
        assert "NON_EXISTENT" in results.unhandled_tags
        assert "NON_EXISTENT" in results.unhandled_extinf_keys

    def test_validation_results_empty_state(self):
        """Empty validation results should report no issues."""
        results = M3uValidationResults()

        assert len(results.unhandled_tags) == 0
        assert len(results.unhandled_extinf_keys) == 0
        assert len(results.channels_without_urls) == 0

    def test_validation_results_realistic_scenario(self):
        """Realistic validation scenario with mixed issues."""
        results = M3uValidationResults()

        # Simulate parsing an M3U with various issues
        results.unhandled_tags["EXT-X-VERSION"] = 1
        results.unhandled_tags["EXT-X-STREAM-INF"] = 3

        results.unhandled_extinf_keys["custom-logo"] = 2
        results.unhandled_extinf_keys["provider-id"] = 1

        results.channels_without_urls = ["Orphaned Channel 1", "Orphaned Channel 2"]

        # Verify all issues are tracked
        assert results.unhandled_tags["EXT-X-VERSION"] == 1
        assert results.unhandled_tags["EXT-X-STREAM-INF"] == 3
        assert results.unhandled_extinf_keys["custom-logo"] == 2
        assert results.unhandled_extinf_keys["provider-id"] == 1
        assert len(results.channels_without_urls) == 2

    def test_validation_results_case_sensitivity(self):
        """Validation results should preserve case sensitivity."""
        results = M3uValidationResults()

        results.unhandled_tags["EXT-X-VERSION"] = 1
        results.unhandled_tags["ext-x-version"] = 1  # Different case

        results.unhandled_extinf_keys["Custom-Attr"] = 1
        results.unhandled_extinf_keys["custom-attr"] = 1  # Different case

        # Should treat different cases as different items
        assert len(results.unhandled_tags) == 2
        assert len(results.unhandled_extinf_keys) == 2
        assert results.unhandled_tags["EXT-X-VERSION"] == 1
        assert results.unhandled_tags["ext-x-version"] == 1
        assert results.unhandled_extinf_keys["Custom-Attr"] == 1
        assert results.unhandled_extinf_keys["custom-attr"] == 1

    def test_log_results_method_exists(self):
        """log_results method should exist and be callable."""
        results = M3uValidationResults()

        # Should not raise an exception
        results.log_results()
        results.log_results("test_context")

    def test_channels_without_urls(self):
        """Channels without URLs should be logged."""
        results = M3uValidationResults()
        results.channels_without_urls = ["Channel 1", "Channel 2"]
        results.log_results()
