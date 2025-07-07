import datetime as dt
from typing import Literal, Dict
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
    if level == "debug":
        logger.debug(f"\t [{func_name}] {message}")
    elif level == "info":
        logger.info(f"\t [{func_name}] {message}")
    elif level == "warning":
        logger.warning(f"\t [{func_name}] {message}")
    elif level == "error":
        logger.error(f"\t [{func_name}] {message}")


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


def format_download_progress_response(progress_data: Dict[str, Dict]) -> Dict[str, "DownloadProgress"]:
    """Format raw progress data into DownloadProgress models"""
    from models.models import DownloadProgress
    return {
        task_id: DownloadProgress(**progress)
        for task_id, progress in progress_data.items()
    }


def format_ingest_progress_response(progress_data: Dict[str, Dict]) -> Dict[str, Dict]:
    """Format raw progress data for ingest endpoints (legacy format)"""
    return {"ingest": progress_data}
