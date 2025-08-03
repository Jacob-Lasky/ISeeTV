import datetime as dt
from typing import Any, Literal

from fastapi import HTTPException, status

from common.log_utils import get_logger
from common.state import get_progress
from models.models import DownloadProgress
from common.filter_utils import FILTERABLE_COLUMNS_CONFIG

logger = get_logger(__name__)


def create_task_id(
    source_name: str,
    file_type: Literal["m3u", "epg"],
    task_type: Literal["download", "ingest"],
) -> str:
    """Create a unique task ID for a source and file type."""
    logger.debug("Creating task for %s, %s, %s", source_name, file_type, task_type)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{task_type}_{file_type}_{source_name}_{timestamp}"


def get_progress_response(task_id: str, task_type: Literal["download", "ingest"]):
    """Get progress data for a specific task by ID and type."""
    progress = get_progress(task_type)
    logger.debug("Getting progress for %s", task_id)
    if task_id not in progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{task_type.title()} task {task_id} not found",
        )
    return progress[task_id]


def get_all_progress_response(task_type: Literal["download", "ingest"]):
    """Get all progress data for a specific task type."""
    logger.debug("Getting all progress for %s", task_type)
    return get_progress(task_type)


def format_download_progress_response(
    progress_data: dict[str, dict],
) -> dict[str, "DownloadProgress"]:
    """Format raw progress data into DownloadProgress models."""
    logger.debug("Formatting download progress response for %s", progress_data)
    return {
        task_id: DownloadProgress(**progress)
        for task_id, progress in progress_data.items()
    }


def format_ingest_progress_response(progress_data: dict[str, dict]) -> dict[str, dict]:
    """Format raw progress data for ingest endpoints (legacy format)."""
    logger.debug("Formatting ingest progress response for %s", progress_data)
    return {"ingest": progress_data}


def format_table_response(
    records: list[dict[str, Any]],
    table_name: str,
    source_filter: str | None = None,
    filter_stats: dict[str, int] | None = None,
) -> dict[str, Any]:
    logger.debug("Formatting table response for %s", table_name)
    
    # Calculate enhanced statistics including tracing data
    total_records = len(records)
    
    # Calculate acceptance statistics
    accepted_records = len([r for r in records if r.get("accepted") is True])
    rejected_records = len([r for r in records if r.get("accepted") is False])
    no_acceptance_data = total_records - accepted_records - rejected_records
    
    # Calculate filter_reasons statistics (JSON format)
    records_with_filter_reasons = 0
    records_with_empty_filter_reasons = 0
    for record in records:
        filter_reasons = record.get("filter_reasons")
        if filter_reasons:
            if isinstance(filter_reasons, dict) and len(filter_reasons) > 0:
                records_with_filter_reasons += 1
            elif isinstance(filter_reasons, str) and filter_reasons not in ["{}", "[]", ""]:
                records_with_filter_reasons += 1
        else:
            records_with_empty_filter_reasons += 1
    
    # Calculate trace statistics
    records_with_trace = len([r for r in records if r.get("_trace") and len(r.get("_trace", [])) > 0])
    records_without_trace = total_records - records_with_trace
    
    # Create comprehensive statistics (no DRY violation)
    comprehensive_stats = {
        "total": total_records,
        "accepted": accepted_records,
        "rejected": rejected_records,
        "with_trace": records_with_trace,
        "with_filter_reasons": records_with_filter_reasons
    }
    
    # Add optional stats only if they exist
    if no_acceptance_data > 0:
        comprehensive_stats["no_acceptance_data"] = no_acceptance_data
    if records_without_trace > 0:
        comprehensive_stats["without_trace"] = records_without_trace
    
    # Use provided filter statistics or fall back to our comprehensive stats
    if filter_stats and len(filter_stats) > 0:
        passed_records = filter_stats.get("Passed", accepted_records)
        filtered_records = filter_stats.get("Filtered", rejected_records)
        # Merge provided stats with our comprehensive stats
        final_stats = {**comprehensive_stats, **filter_stats}
    else:
        passed_records = accepted_records
        filtered_records = rejected_records
        final_stats = comprehensive_stats

    return {
        "success": True,
        "data": {
            "records": records,
            "total": total_records,
            "passed": passed_records,
            "filtered": filtered_records,
            "stats": final_stats,
            "table_name": table_name,
            "source_filter": source_filter
        },
    }


def validate_table_name(table_name: str, include_streams: bool = True) -> None:
    """Unified table name validation to prevent SQL injection.

    Args:
        table_name: Name of the table to validate
        include_streams: Whether to include 'streams' as a valid table

    Raises:
        HTTPException: If table name is invalid

    """
    valid_tables = list(FILTERABLE_COLUMNS_CONFIG.keys())
    if not include_streams:
        valid_tables = [t for t in valid_tables if t != "streams"]

    if table_name not in valid_tables:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid table name. Must be one of: {valid_tables}",
        )
