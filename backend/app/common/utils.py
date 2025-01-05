import hashlib


def generate_channel_id(tvg_id: str | None, name: str, logo: str) -> str:
    """Generate a unique channel ID prioritizing tvg-id if available"""
    if tvg_id:
        # Use tvg-id directly as it's already a good unique identifier
        return tvg_id
    else:
        # Fallback to generate a unique ID for channels without tvg-id
        unique_string = f"{name}:{logo}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
