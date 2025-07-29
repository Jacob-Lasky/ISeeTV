"""Tests for ValidationResults class following atomic design principles.

This module focuses exclusively on testing ValidationResults functionality.
Each test validates one specific behavior or edge case.
"""

import pytest
from unittest.mock import patch, MagicMock

from ingest.epg_parser import ValidationResults


class TestValidationResults:
    """Atomic tests for ValidationResults class."""

    def test_initialization(self):
        """ValidationResults should initialize with empty collections."""
        results = ValidationResults()
        
        assert len(results.unexpected_root_tags) == 0
        assert len(results.unexpected_root_attrs) == 0
        assert len(results.unexpected_channel_tags) == 0
        assert len(results.unexpected_channel_attrs) == 0
        assert len(results.unexpected_programme_tags) == 0
        assert len(results.unexpected_programme_attrs) == 0

    def test_unexpected_root_tags_accumulation(self):
        """Unexpected root tags should accumulate counts correctly."""
        results = ValidationResults()
        
        results.unexpected_root_tags["unknown_tag"] += 1
        results.unexpected_root_tags["unknown_tag"] += 1
        results.unexpected_root_tags["other_tag"] += 1
        
        assert results.unexpected_root_tags["unknown_tag"] == 2
        assert results.unexpected_root_tags["other_tag"] == 1

    def test_unexpected_root_attrs_collection(self):
        """Unexpected root attributes should be collected in set."""
        results = ValidationResults()
        
        results.unexpected_root_attrs.add("unknown_attr")
        results.unexpected_root_attrs.add("other_attr")
        results.unexpected_root_attrs.add("unknown_attr")  # Duplicate
        
        assert len(results.unexpected_root_attrs) == 2
        assert "unknown_attr" in results.unexpected_root_attrs
        assert "other_attr" in results.unexpected_root_attrs

    def test_unexpected_channel_attrs_by_id(self):
        """Channel attributes should be tracked per channel ID."""
        results = ValidationResults()
        
        results.unexpected_channel_attrs["channel1"].add("unknown_attr")
        results.unexpected_channel_attrs["channel1"].add("other_attr")
        results.unexpected_channel_attrs["channel2"].add("unknown_attr")
        
        assert len(results.unexpected_channel_attrs["channel1"]) == 2
        assert len(results.unexpected_channel_attrs["channel2"]) == 1
        assert "unknown_attr" in results.unexpected_channel_attrs["channel1"]
        assert "other_attr" in results.unexpected_channel_attrs["channel1"]

    def test_unexpected_programme_attrs_by_id(self):
        """Programme attributes should be tracked per programme ID."""
        results = ValidationResults()
        
        results.unexpected_programme_attrs["prog1"].add("unknown_attr")
        results.unexpected_programme_attrs["prog1"].add("other_attr")
        results.unexpected_programme_attrs["prog2"].add("unknown_attr")
        
        assert len(results.unexpected_programme_attrs["prog1"]) == 2
        assert len(results.unexpected_programme_attrs["prog2"]) == 1

    def test_defaultdict_behavior(self):
        """ValidationResults should use defaultdict for automatic initialization."""
        results = ValidationResults()
        
        # Accessing non-existent keys should auto-initialize
        results.unexpected_root_tags["new_tag"] += 1
        results.unexpected_channel_tags["new_channel_tag"] += 1
        results.unexpected_programme_tags["new_programme_tag"] += 1
        
        assert results.unexpected_root_tags["new_tag"] == 1
        assert results.unexpected_channel_tags["new_channel_tag"] == 1
        assert results.unexpected_programme_tags["new_programme_tag"] == 1

    def test_defaultdict_set_behavior(self):
        """ValidationResults should use defaultdict(set) for attribute collections."""
        results = ValidationResults()
        
        # Accessing non-existent keys should auto-initialize sets
        results.unexpected_channel_attrs["new_channel"].add("attr1")
        results.unexpected_programme_attrs["new_programme"].add("attr1")
        
        assert "attr1" in results.unexpected_channel_attrs["new_channel"]
        assert "attr1" in results.unexpected_programme_attrs["new_programme"]
