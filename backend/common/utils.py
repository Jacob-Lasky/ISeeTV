import datetime as dt
from typing import Any, Literal

from fastapi import HTTPException, status

from common.state import get_progress
from models.models import DownloadProgress
from common.log_utils import get_logger

logger = get_logger(__name__)


def create_task_id(
    source_name: str,
    file_type: Literal["m3u", "epg"],
    task_type: Literal["download", "ingest"],
):
    """Create a unique task ID for a source and file type"""
    logger.info("Creating task for %s, %s, %s", source_name, file_type, task_type)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{task_type}_{file_type}_{source_name}_{timestamp}"


def get_progress_response(task_id: str, task_type: Literal["download", "ingest"]):
    """Get progress data for a specific task by ID and type"""
    progress = get_progress(task_type)
    logger.debug("Getting progress for %s", task_id)
    if task_id not in progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{task_type.title()} task {task_id} not found",
        )
    return progress[task_id]


def get_all_progress_response(task_type: Literal["download", "ingest"]):
    """Get all progress data for a specific task type"""
    logger.debug("Getting all progress for %s", task_type)
    return get_progress(task_type)


def format_download_progress_response(
    progress_data: dict[str, dict],
) -> dict[str, "DownloadProgress"]:
    """Format raw progress data into DownloadProgress models"""
    logger.debug("Formatting download progress response for %s", progress_data)
    return {
        task_id: DownloadProgress(**progress)
        for task_id, progress in progress_data.items()
    }


def format_ingest_progress_response(progress_data: dict[str, dict]) -> dict[str, dict]:
    """Format raw progress data for ingest endpoints (legacy format)"""
    logger.debug("Formatting ingest progress response for %s", progress_data)
    return {"ingest": progress_data}


def format_table_response(
    records: list[dict[str, Any]],
    table_name: str,
    source_filter: str | None = None,
    filter_stats: dict[str, int] | None = None,
) -> dict[str, Any]:
    logger.debug("Formatting table response for %s", table_name)
    # Use provided filter statistics or calculate from records
    if filter_stats and len(filter_stats) > 0:
        total_records = sum(filter_stats.values())
        passed_records = filter_stats.get("Passed", 0)
        filtered_records = total_records - passed_records
    else:
        # Fallback to calculating from returned records
        total_records = len(records)
        passed_records = len([r for r in records if r.get("filter_reasons") == "[]"])
        filtered_records = total_records - passed_records
        # If no filter_stats provided, create basic stats from records
        if not filter_stats:
            filter_stats = {}
            if passed_records > 0:
                filter_stats["Passed"] = passed_records
            if filtered_records > 0:
                filter_stats["Filtered"] = filtered_records

    return {
        "success": True,
        "data": {
            "records": records,
            "total": total_records,
            "passed": passed_records,
            "filtered": filtered_records,
            "filter_stats": filter_stats or {},
            "table_name": table_name,
            "source_filter": source_filter,
        },
    }
