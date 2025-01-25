import os
import subprocess
import threading
from typing import Any
from typing import Optional

import requests

from app.common.logger import Logger

logger = Logger(
    "ISeeTV-VideoHelpers",
    os.environ.get("VERBOSE", "false"),
    os.environ.get("LOG_LEVEL", "INFO"),
    color="LIGHT_BLUE",
)


def dict_to_ffmpeg_command(params: dict[str, Optional[str]]) -> list[str]:
    command = ["ffmpeg"]
    # Add all parameters except output
    for key, value in params.items():
        if key != "output":
            command.append(key)
            if value is not None:
                command.append(value)
    # Add output file last
    if "output" in params and params["output"] is not None:
        command.append(params["output"])
    return command


class StreamMonitor:
    def __init__(self, process: subprocess.Popen[Any]) -> None:
        self.process = process
        self.stop_flag = False
        self._thread: Optional[threading.Thread] = None
        self.logger = Logger(
            "ISeeTV-StreamMonitor",
            os.environ.get("VERBOSE", "false"),
            os.environ.get("LOG_LEVEL", "INFO"),
            color="BLUE",
        )

    def start(self) -> None:
        self.logger.info("Starting stream monitor")
        self._thread = threading.Thread(target=self._monitor)
        self._thread.daemon = True
        self._thread.start()

    def stop(self) -> None:
        self.logger.info("Stopping stream monitor")
        self.stop_flag = True
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

    def _monitor(self) -> None:
        while not self.stop_flag:
            if self.process.poll() is not None:
                self.logger.error(
                    f"FFmpeg process ended with code {self.process.returncode}"
                )
                break

            if self.process.stderr:  # Check if stderr exists
                line = self.process.stderr.readline()
                if line:
                    line_str = line.strip()
                    if line_str:
                        self.logger.debug(f"FFmpeg: {line_str}")

            if self.stop_flag:
                break


async def process_video(
    stream_url: str, output_dir: str, m3u8_name: str, guide_id: str
) -> tuple[subprocess.Popen[Any], StreamMonitor]:
    output_m3u8 = os.path.join(output_dir, m3u8_name)

    # Get correct stream url
    response = requests.get(stream_url, allow_redirects=True)
    redirected_url = response.url

    ffmpeg_params: dict[str, Optional[str]] = {
        "-y": None,  # Overwrite output files
        "-i": redirected_url,
        # Video settings
        "-c:v": "copy",  # Use stream copy for video
        "-c:a": "aac",  # Convert audio to AAC
        "-ar": "44100",  # Audio sample rate
        "-ac": "2",  # Stereo audio
        "-b:a": "128k",  # Audio bitrate
        # HLS settings
        "-f": "hls",
        "-hls_time": "4",
        "-hls_list_size": "0",
        "-hls_flags": "append_list+omit_endlist",
        "-hls_segment_filename": os.path.join(output_dir, "stream_%06d.ts"),
        "-hls_base_url": f"/segments/{guide_id}/",
        "-hls_segment_type": "mpegts",
        # Stream settings
        "-reconnect": "1",
        "-reconnect_streamed": "1",
        "-reconnect_delay_max": "10",
        # Output file
        "output": output_m3u8,
    }

    command_list = dict_to_ffmpeg_command(ffmpeg_params)
    logger.debug(f"FFmpeg command: {command_list}")

    # Create process with full stderr logging
    process = subprocess.Popen(
        command_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,  # This helps with reading the output
    )

    # Create and start monitor
    monitor = StreamMonitor(process)
    monitor.start()

    return process, monitor
