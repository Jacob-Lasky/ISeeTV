"""Tests for _get_filter_query function following atomic design principles."""

import pytest

from common.filter_utils import (
    SPECIAL_FILTER_QUERIES,
    _get_filter_query,
)


class TestGetFilterQuery:
    """Test the _get_filter_query function."""

    @pytest.mark.parametrize("table_name,column_name", [
        ("streams", "source"),
        ("streams", "group"),
        ("streams", "stream_mode"),
        ("streams", "filter_reasons"),
    ])
    def test_special_queries(self, table_name, column_name):
        """Test that special queries are returned for streams table."""
        result = _get_filter_query(table_name, column_name)
        expected = SPECIAL_FILTER_QUERIES[table_name][column_name]
        assert result == expected

    @pytest.mark.parametrize("table_name", [
        "epg_channels",
        "m3u_channels", 
        "programs",
    ])
    def test_filter_reasons_query(self, table_name):
        """Test filter_reasons query generation for regular tables."""
        result = _get_filter_query(table_name, "filter_reasons")
        assert "WITH filter_values AS" in result
        assert "CASE" in result
        assert "WHEN filter_reasons IS NULL" in result
        assert "THEN 'Passed'" in result
        assert f"FROM {table_name}" in result

    @pytest.mark.parametrize("table_name,column_name", [
        ("epg_channels", "source"),
        ("m3u_channels", "group"),
        ("programs", "source"),
    ])
    def test_standard_column_query(self, table_name, column_name):
        """Test standard column query generation."""
        result = _get_filter_query(table_name, column_name)
        assert f"SELECT `{column_name}` as value, COUNT(*) as count" in result
        assert f"FROM {table_name}" in result
        assert f"WHERE `{column_name}` IS NOT NULL" in result
        assert f"GROUP BY `{column_name}`" in result
        assert f"ORDER BY `{column_name}`" in result

    def test_column_name_escaping(self):
        """Test that column names are properly escaped with backticks."""
        result = _get_filter_query("test_table", "test_column")
        assert "`test_column`" in result

    def test_empty_strings(self):
        """Test handling of empty table and column names."""
        result = _get_filter_query("", "")
        assert "SELECT `` as value" in result
