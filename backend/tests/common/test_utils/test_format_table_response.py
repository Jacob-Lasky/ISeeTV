"""
Tests for format_table_response function from common.utils.

Following atomic design principles:
- Single responsibility: Tests only format_table_response function
- Pure functions: Each test validates one specific behavior
- No side effects: Tests are isolated and independent
"""

import pytest
from unittest.mock import patch

from common.utils import format_table_response


class TestFormatTableResponse:
    """Test class for format_table_response function."""

    def test_format_table_response_with_filter_stats(self):
        """Test formatting with provided filter statistics."""
        records = [
            {"id": 1, "name": "Channel 1", "filter_reasons": "[]"},
            {"id": 2, "name": "Channel 2", "filter_reasons": "[\"blocked\"]"},
            {"id": 3, "name": "Channel 3", "filter_reasons": "[]"}
        ]
        filter_stats = {"Passed": 2, "Blocked": 1}
        
        result = format_table_response(
            records=records,
            table_name="m3u_channels",
            source_filter="test_source",
            filter_stats=filter_stats
        )
        
        expected = {
            "success": True,
            "data": {
                "records": records,
                "total": 3,
                "passed": 2,
                "filtered": 1,
                "filter_stats": filter_stats,
                "table_name": "m3u_channels",
                "source_filter": "test_source"
            }
        }
        assert result == expected

    def test_format_table_response_without_filter_stats(self):
        """Test formatting without provided filter statistics (fallback calculation)."""
        records = [
            {"id": 1, "name": "Channel 1", "filter_reasons": "[]"},
            {"id": 2, "name": "Channel 2", "filter_reasons": "[\"blocked\"]"},
            {"id": 3, "name": "Channel 3", "filter_reasons": "[]"},
            {"id": 4, "name": "Channel 4", "filter_reasons": "[\"adult\", \"duplicate\"]"}
        ]
        
        result = format_table_response(
            records=records,
            table_name="m3u_channels",
            source_filter="test_source"
        )
        
        expected = {
            "success": True,
            "data": {
                "records": records,
                "total": 4,
                "passed": 2,  # Records with filter_reasons == "[]"
                "filtered": 2,  # Records with non-empty filter_reasons
                "filter_stats": {"Passed": 2, "Filtered": 2},
                "table_name": "m3u_channels",
                "source_filter": "test_source"
            }
        }
        assert result == expected

    def test_format_table_response_empty_records(self):
        """Test formatting with empty records list."""
        records = []
        filter_stats = {}
        
        result = format_table_response(
            records=records,
            table_name="programs",
            filter_stats=filter_stats
        )
        
        expected = {
            "success": True,
            "data": {
                "records": [],
                "total": 0,
                "passed": 0,
                "filtered": 0,
                "filter_stats": {},
                "table_name": "programs",
                "source_filter": None
            }
        }
        assert result == expected

    def test_format_table_response_all_passed_records(self):
        """Test formatting when all records pass filters."""
        records = [
            {"id": 1, "name": "Channel 1", "filter_reasons": "[]"},
            {"id": 2, "name": "Channel 2", "filter_reasons": "[]"},
            {"id": 3, "name": "Channel 3", "filter_reasons": "[]"}
        ]
        
        result = format_table_response(
            records=records,
            table_name="epg_channels"
        )
        
        expected = {
            "success": True,
            "data": {
                "records": records,
                "total": 3,
                "passed": 3,
                "filtered": 0,
                "filter_stats": {"Passed": 3},
                "table_name": "epg_channels",
                "source_filter": None
            }
        }
        assert result == expected

    def test_format_table_response_all_filtered_records(self):
        """Test formatting when all records are filtered."""
        records = [
            {"id": 1, "name": "Channel 1", "filter_reasons": "[\"blocked\"]"},
            {"id": 2, "name": "Channel 2", "filter_reasons": "[\"adult\"]"},
            {"id": 3, "name": "Channel 3", "filter_reasons": "[\"duplicate\", \"low_quality\"]"}
        ]
        
        result = format_table_response(
            records=records,
            table_name="m3u_channels"
        )
        
        expected = {
            "success": True,
            "data": {
                "records": records,
                "total": 3,
                "passed": 0,
                "filtered": 3,
                "filter_stats": {"Filtered": 3},
                "table_name": "m3u_channels",
                "source_filter": None
            }
        }
        assert result == expected

    def test_format_table_response_empty_filter_stats_provided(self):
        """Test formatting with empty filter stats provided."""
        records = [
            {"id": 1, "name": "Channel 1", "filter_reasons": "[]"},
            {"id": 2, "name": "Channel 2", "filter_reasons": "[\"blocked\"]"}
        ]
        filter_stats = {}
        
        result = format_table_response(
            records=records,
            table_name="m3u_channels",
            filter_stats=filter_stats
        )
        
        # Should fall back to calculating from records since filter_stats is empty
        expected = {
            "success": True,
            "data": {
                "records": records,
                "total": 2,
                "passed": 1,
                "filtered": 1,
                "filter_stats": {"Passed": 1, "Filtered": 1},
                "table_name": "m3u_channels",
                "source_filter": None
            }
        }
        assert result == expected

    def test_format_table_response_complex_filter_stats(self):
        """Test formatting with complex filter statistics."""
        records = []  # Records can be empty when using provided filter stats
        filter_stats = {
            "Passed": 1500,
            "Blocked": 200,
            "Adult": 150,
            "Duplicate": 100,
            "Low Quality": 50
        }
        
        result = format_table_response(
            records=records,
            table_name="m3u_channels",
            source_filter="large_source",
            filter_stats=filter_stats
        )
        
        expected = {
            "success": True,
            "data": {
                "records": records,
                "total": 2000,  # Sum of all filter stats
                "passed": 1500,
                "filtered": 500,  # Total - passed
                "filter_stats": filter_stats,
                "table_name": "m3u_channels",
                "source_filter": "large_source"
            }
        }
        assert result == expected

    def test_format_table_response_missing_filter_reasons(self):
        """Test formatting with records missing filter_reasons field."""
        records = [
            {"id": 1, "name": "Channel 1"},  # Missing filter_reasons
            {"id": 2, "name": "Channel 2", "filter_reasons": "[]"},
            {"id": 3, "name": "Channel 3", "filter_reasons": None}  # None filter_reasons
        ]
        
        result = format_table_response(
            records=records,
            table_name="m3u_channels"
        )
        
        # Only records with filter_reasons == "[]" should count as passed
        expected = {
            "success": True,
            "data": {
                "records": records,
                "total": 3,
                "passed": 1,  # Only the record with filter_reasons == "[]"
                "filtered": 2,
                "filter_stats": {"Passed": 1, "Filtered": 2},
                "table_name": "m3u_channels",
                "source_filter": None
            }
        }
        assert result == expected

    @pytest.mark.parametrize(
        "table_name,source_filter",
        [
            ("m3u_channels", "source1"),
            ("epg_channels", "source2"),
            ("programs", "source3"),
            ("streams", None),
            ("test_table", ""),
            ("", "test_source"),
        ],
    )
    def test_format_table_response_various_table_names_and_sources(self, table_name, source_filter):
        """Test formatting with various table names and source filters."""
        records = [{"id": 1, "filter_reasons": "[]"}]
        
        result = format_table_response(
            records=records,
            table_name=table_name,
            source_filter=source_filter
        )
        
        assert result["success"] is True
        assert result["data"]["table_name"] == table_name
        assert result["data"]["source_filter"] == source_filter

    def test_format_table_response_large_dataset(self):
        """Test formatting with large dataset."""
        # Create large dataset
        records = []
        for i in range(1000):
            filter_reasons = "[]" if i % 3 == 0 else "[\"blocked\"]"
            records.append({
                "id": i,
                "name": f"Channel {i}",
                "filter_reasons": filter_reasons
            })
        
        result = format_table_response(
            records=records,
            table_name="m3u_channels"
        )
        
        expected_passed = len([r for r in records if r["filter_reasons"] == "[]"])
        expected_filtered = 1000 - expected_passed
        
        assert result["data"]["total"] == 1000
        assert result["data"]["passed"] == expected_passed
        assert result["data"]["filtered"] == expected_filtered
        assert len(result["data"]["records"]) == 1000

    def test_format_table_response_unicode_data(self):
        """Test formatting with unicode characters in data."""
        records = [
            {"id": 1, "name": "频道 1", "filter_reasons": "[]"},
            {"id": 2, "name": "Canal 2 🎬", "filter_reasons": "[\"блокировано\"]"},
            {"id": 3, "name": "チャンネル3", "filter_reasons": "[]"}
        ]
        
        result = format_table_response(
            records=records,
            table_name="国际频道",
            source_filter="测试源"
        )
        
        assert result["success"] is True
        assert result["data"]["table_name"] == "国际频道"
        assert result["data"]["source_filter"] == "测试源"
        assert result["data"]["records"][0]["name"] == "频道 1"
        assert result["data"]["records"][1]["name"] == "Canal 2 🎬"
