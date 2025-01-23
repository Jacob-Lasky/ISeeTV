import hashlib
import re


def generate_channel_id(tvg_id: str | None, name: str) -> str:
    """Generate a unique channel ID prioritizing tvg-id if available"""
    # sanitize id and name for a url
    if tvg_id:
        tvg_id = re.sub(r"[^a-zA-Z0-9]+", "-", tvg_id)
    else:
        tvg_id = "no-id"

    name = re.sub(r"[^a-zA-Z0-9]+", "-", name)

    return f"{tvg_id}-{name}"
