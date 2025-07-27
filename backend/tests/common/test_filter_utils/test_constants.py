"""Tests for filter_utils constants following atomic design principles."""

import pytest

from common.filter_utils import (
    FILTERABLE_COLUMNS_CONFIG,
    SPECIAL_FILTER_QUERIES,
)


class TestFilterableColumnsConfig:
    """Test the FILTERABLE_COLUMNS_CONFIG constant."""

    def test_config_structure(self):
        """Test that config has expected structure and values."""
        assert isinstance(FILTERABLE_COLUMNS_CONFIG, dict)
        assert "epg_channels" in FILTERABLE_COLUMNS_CONFIG
        assert "m3u_channels" in FILTERABLE_COLUMNS_CONFIG
        assert "programs" in FILTERABLE_COLUMNS_CONFIG
        assert "streams" in FILTERABLE_COLUMNS_CONFIG

    def test_config_values(self):
        """Test that config contains expected column lists."""
        assert FILTERABLE_COLUMNS_CONFIG["epg_channels"] == ["source", "filter_reasons"]
        assert FILTERABLE_COLUMNS_CONFIG["m3u_channels"] == ["source", "group", "stream_mode", "filter_reasons"]
        assert FILTERABLE_COLUMNS_CONFIG["programs"] == ["source", "filter_reasons"]
        assert FILTERABLE_COLUMNS_CONFIG["streams"] == ["source", "group", "stream_mode", "filter_reasons"]


class TestSpecialFilterQueries:
    """Test the SPECIAL_FILTER_QUERIES constant."""

    def test_streams_queries_exist(self):
        """Test that streams table has special queries defined."""
        assert "streams" in SPECIAL_FILTER_QUERIES
        streams_queries = SPECIAL_FILTER_QUERIES["streams"]
        assert "source" in streams_queries
        assert "group" in streams_queries
        assert "stream_mode" in streams_queries
        assert "filter_reasons" in streams_queries

    def test_query_structure(self):
        """Test that queries are properly formatted SQL strings."""
        for table, columns in SPECIAL_FILTER_QUERIES.items():
            for column, query in columns.items():
                assert isinstance(query, str)
                assert "SELECT" in query.upper()
