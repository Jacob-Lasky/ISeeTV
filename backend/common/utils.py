import datetime as dt
from typing import Literal, Dict, List, Any, Optional
import logging
import inspect
from fastapi import HTTPException, status
from common.state import get_progress

logger = logging.getLogger(__name__)


def create_task_id(
    source_name: str,
    file_type: Literal["m3u", "epg"],
    task_type: Literal["download", "ingest"],
):
    """Create a unique task ID for a source and file type"""
    log_function(f"Creating task for {source_name}, {file_type}, {task_type}")
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{task_type}_{file_type}_{source_name}_{timestamp}"


def log_function(
    message: str = "",
    level: Literal["debug", "info", "warning", "error"] = "info",
):
    func_name = inspect.currentframe().f_back.f_code.co_name  # type: ignore
    log_message = f"\t [{func_name}]: {message}"
    if level == "debug":
        logger.debug(log_message)
    elif level == "info":
        logger.info(log_message)
    elif level == "warning":
        logger.warning(log_message)
    elif level == "error":
        logger.error(log_message)


def get_progress_response(task_id: str, task_type: Literal["download", "ingest"]):
    """Get progress data for a specific task by ID and type"""
    progress = get_progress(task_type)
    if task_id not in progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{task_type.title()} task {task_id} not found",
        )
    return progress[task_id]


def get_all_progress_response(task_type: Literal["download", "ingest"]):
    """Get all progress data for a specific task type"""
    return get_progress(task_type)


def format_download_progress_response(
    progress_data: Dict[str, Dict],
) -> Dict[str, "DownloadProgress"]:
    """Format raw progress data into DownloadProgress models"""
    from models.models import DownloadProgress

    return {
        task_id: DownloadProgress(**progress)
        for task_id, progress in progress_data.items()
    }


def format_ingest_progress_response(progress_data: Dict[str, Dict]) -> Dict[str, Dict]:
    """Format raw progress data for ingest endpoints (legacy format)"""
    return {"ingest": progress_data}


def format_table_response(
    records: List[Dict[str, Any]],
    table_name: str,
    source_filter: Optional[str] = None,
    filter_stats: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    # Use provided filter statistics or calculate from records
    if filter_stats and len(filter_stats) > 0:
        total_records = sum(filter_stats.values())
        passed_records = filter_stats.get("Passed", 0)
        filtered_records = total_records - passed_records
    else:
        # Fallback to calculating from returned records
        total_records = len(records)
        passed_records = len([r for r in records if r.get("filter_reasons") is None or r.get("filter_reasons") == '[]' or r.get("filter_reasons") == ''])
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
