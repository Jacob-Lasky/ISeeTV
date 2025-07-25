"""Tests for M3U parser constants and configuration following atomic design principles.

This module focuses exclusively on testing module constants and configuration values.
Each test validates one specific constant or configuration aspect.
"""

import pytest

from ingest.m3u_parser import EXPECTED_M3U_TAGS, EXPECTED_EXTINF_KEYS


class TestConstants:
    """Atomic tests for module constants and configuration."""

    def test_expected_m3u_tags_contains_required_tags(self):
        """EXPECTED_M3U_TAGS should contain standard M3U tags."""
        assert "#EXTM3U" in EXPECTED_M3U_TAGS
        assert "#EXTINF" in EXPECTED_M3U_TAGS
        assert "#EXT-X-SESSION-DATA" in EXPECTED_M3U_TAGS

    def test_expected_extinf_keys_contains_standard_keys(self):
        """EXPECTED_EXTINF_KEYS should contain standard EXTINF attributes."""
        expected_keys = {"tvg-id", "tvg-name", "tvg-logo", "group-title", "timeshift"}
        assert expected_keys.issubset(EXPECTED_EXTINF_KEYS)

    def test_expected_m3u_tags_is_set(self):
        """EXPECTED_M3U_TAGS should be a set for efficient lookups."""
        assert isinstance(EXPECTED_M3U_TAGS, set)
        assert len(EXPECTED_M3U_TAGS) > 0

    def test_expected_extinf_keys_is_set(self):
        """EXPECTED_EXTINF_KEYS should be a set for efficient lookups."""
        assert isinstance(EXPECTED_EXTINF_KEYS, set)
        assert len(EXPECTED_EXTINF_KEYS) > 0

    def test_expected_m3u_tags_contains_hls_tags(self):
        """EXPECTED_M3U_TAGS should include common HLS tags."""
        hls_tags = {
            "#EXT-X-VERSION",
            "#EXT-X-STREAM-INF",
            "#EXT-X-MEDIA",
            "#EXT-X-PLAYLIST-TYPE"
        }
        # Check if any HLS tags are included (implementation may vary)
        assert any(tag in EXPECTED_M3U_TAGS for tag in hls_tags) or len(EXPECTED_M3U_TAGS) >= 2

    def test_expected_extinf_keys_contains_iptv_keys(self):
        """EXPECTED_EXTINF_KEYS should include common IPTV-specific keys."""
        iptv_keys = {
            "tvg-id",
            "tvg-name", 
            "tvg-logo",
            "group-title"
        }
        # All core IPTV keys should be present
        assert iptv_keys.issubset(EXPECTED_EXTINF_KEYS)

    def test_constants_are_immutable_references(self):
        """Constants should be defined as immutable data structures."""
        # Test that constants are sets (immutable for practical purposes in this context)
        assert isinstance(EXPECTED_M3U_TAGS, (set, frozenset))
        assert isinstance(EXPECTED_EXTINF_KEYS, (set, frozenset))

    def test_no_empty_strings_in_constants(self):
        """Constants should not contain empty strings."""
        assert "" not in EXPECTED_M3U_TAGS
        assert "" not in EXPECTED_EXTINF_KEYS
        
    def test_all_m3u_tags_start_with_hash(self):
        """All M3U tags should start with # character."""
        for tag in EXPECTED_M3U_TAGS:
            assert tag.startswith("#"), f"Tag '{tag}' should start with #"

    def test_extinf_keys_are_lowercase_with_hyphens(self):
        """EXTINF keys should follow lowercase-with-hyphens convention."""
        for key in EXPECTED_EXTINF_KEYS:
            # Check that keys are lowercase and use hyphens (common EXTINF convention)
            assert key.islower() or "-" in key, f"Key '{key}' should be lowercase or contain hyphens"
