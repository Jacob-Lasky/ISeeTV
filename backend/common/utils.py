from datetime import datetime
from typing import Literal
import logging
import inspect

logger = logging.getLogger(__name__)


def create_task_id(source_name: str, file_type: Literal["m3u", "epg"]):
    """Create a unique task ID for a source and file type"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{file_type}_{source_name}_{timestamp}"


def log_info(message: str = ""):
    func_name = inspect.currentframe().f_back.f_code.co_name
    logger.info(f"\t [{func_name}] {message}")
