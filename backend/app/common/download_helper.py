import os
from collections.abc import AsyncGenerator
from typing import Literal
from typing import TypedDict

import aiohttp

from app.common.logger import Logger

logger = Logger(
    "ISeeTV-DownloadHelper",
    os.environ.get("VERBOSE", "false"),
    os.environ.get("LOG_LEVEL", "INFO"),
    color="LIGHT_BLUE",
)


class ProgressDict(TypedDict):
    type: Literal["progress"]
    current: int
    total: int


async def stream_download(
    url: str, expected_size: int, output_file: str
) -> AsyncGenerator[ProgressDict, None]:
    """
    Download a file and stream progress updates.

    Args:
        url: URL to download from
        expected_size: Expected file size (for progress calculation)
        output_file: Path to save the downloaded file

    Yields:
        Progress updates as dicts with current and total bytes
    """
    try:
        content: list[bytes] = []
        total_bytes = 0
        chunk_count = 0
        last_progress = -1  # Track last progress percentage

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if not response.ok:
                    raise Exception(f"HTTP {response.status}: {response.reason}")

                total = expected_size or response.content_length or 10**9

                async for chunk in response.content.iter_chunked(8192):
                    chunk_count += 1
                    content.append(chunk)
                    total_bytes += len(chunk)

                    # Only yield progress if percentage has changed
                    current_progress = int((total_bytes / total) * 100) if total else 0
                    if current_progress > last_progress:
                        progress_response = ProgressDict(
                            type="progress",
                            current=total_bytes,
                            total=total,
                        )
                        yield progress_response
                        last_progress = current_progress

        logger.info(
            f"Download complete. {chunk_count} chunks, {total_bytes} bytes total"
        )
        content_str = b"".join(content).decode("utf-8")

        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content_str)

    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        # Clean up partial file if it exists
        if os.path.exists(output_file):
            os.remove(output_file)
        raise
