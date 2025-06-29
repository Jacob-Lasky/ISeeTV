import datetime as dt
from typing import Literal
import logging
import inspect
from fastapi import HTTPException, status
from common.state import get_progress

logger = logging.getLogger(__name__)


def create_task_id(
    source_name: str,
    file_type: Literal["m3u", "epg"],
    task_type: Literal["download", "parse"],
):
    """Create a unique task ID for a source and file type"""
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{task_type}_{file_type}_{source_name}_{timestamp}"


def log_info(message: str = ""):
    func_name = inspect.currentframe().f_back.f_code.co_name  # type: ignore
    logger.info(f"\t [{func_name}] {message}")


def get_progress_response(task_id: str, task_type: Literal["download", "ingest"]):
    progress = get_progress(task_type)
    if task_id not in progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{task_type.title()} task {task_id} not found",
        )
    return progress[task_id]
