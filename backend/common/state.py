"""
This module provides a centralized location for global state that needs to be
accessed across multiple modules.
"""

from typing import Dict

# Global state for tracking download progress
# This is the single source of truth for all download progress data
download_progress: Dict[str, Dict] = {}


def get_download_progress() -> Dict[str, Dict]:
    """Get the global download progress dictionary"""
    return download_progress


def clear_download_progress() -> None:
    """Clear all download progress (useful for testing)"""
    global download_progress
    download_progress.clear()
