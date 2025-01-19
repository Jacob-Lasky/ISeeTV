import subprocess
from fastapi import HTTPException
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(asctime)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


async def get_video_codec(url: str) -> str:
    logger.info(f"Determining video codec for {url}")
    try:
        result = subprocess.run(
            [
                "ffprobe",
                # "-headers",
                # "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
                "-i",
                url,
                "-show_streams",
                "-select_streams",
                "v",
                "-show_entries",
                "stream=codec_name",
                "-of",
                "csv=p=0",
                "-loglevel",
                "error",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Log the error and raise an HTTP exception
        logger.error(f"FFprobe failed: {e.stderr}")
        raise HTTPException(status_code=500, detail="Failed to analyze video codec.")


def transcode_audio_only(stream_url: str, channel_dir: str, guide_id: str):
    output_m3u8 = os.path.join(channel_dir, "output.m3u8")
    segment_pattern = os.path.join(channel_dir, "segment%06d.ts")

    process = subprocess.Popen(
        [
            "ffmpeg",
            "-reconnect", "1",
            "-reconnect_streamed", "1", 
            "-reconnect_delay_max", "10",
            "-i", stream_url,
            "-c:v", "copy",
            "-c:a", "aac",
            "-ar", "44100",
            "-b:a", "128k",
            "-ac", "2",
            "-f", "hls",
            "-hls_time", "4",
            "-hls_list_size", "0",
            "-hls_flags", "append_list",
            "-hls_segment_filename", segment_pattern,
            "-hls_base_url", f"/segments/{guide_id}/",
            "-timeout", "10",
            output_m3u8,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    return process, output_m3u8


def transcode_video(url: str, gpu_available: bool):
    if gpu_available:
        logger.debug("GPU detected. Using GPU for transcoding.")
        raise NotImplementedError("GPU transcoding is not implemented yet.")
        # return transcode_with_gpu(url)
    else:
        logger.debug("No GPU detected. Using CPU for transcoding.")
        raise NotImplementedError("CPU transcoding is not implemented yet.")
        # return transcode_to_h264(url)
