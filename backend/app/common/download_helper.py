import aiohttp
import logging
import os

logger = logging.getLogger(__name__)


async def stream_download(url: str, expected_size: int, output_file: str):
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
        content = []
        total_bytes = 0
        chunk_count = 0

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if not response.ok:
                    raise Exception(f"HTTP {response.status}: {response.reason}")

                async for chunk in response.content.iter_chunked(8192):
                    chunk_count += 1
                    content.append(chunk)
                    total_bytes += len(chunk)

                    yield {
                        "type": "progress",
                        "current": total_bytes,
                        "total": expected_size or response.content_length or 0,
                    }

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
