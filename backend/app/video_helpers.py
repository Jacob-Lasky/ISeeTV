import threading
import logging
import sys
import os
import requests
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(asctime)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def dict_to_ffmpeg_command(params: dict) -> list:
    command = ["ffmpeg"]
    # Add all parameters except output
    for key, value in params.items():
        if key != "output":
            command.append(key)
            if value is not None:
                command.append(value)
    # Add output file last
    if "output" in params:
        command.append(params["output"])
    return command


class StreamMonitor:
    def __init__(self, process: subprocess.Popen):
        self.process = process
        self.stop_flag = False
        self._thread = None
        self.logger = logging.getLogger(__name__)

    def start(self):
        self._thread = threading.Thread(target=self._monitor)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self.stop_flag = True
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

    def _monitor(self):
        while not self.stop_flag:
            if self.process.poll() is not None:
                self.logger.error(
                    f"FFmpeg process ended with code {self.process.returncode}"
                )
                break

            line = self.process.stderr.readline()
            if line:
                line = line.strip()
                if line:
                    self.logger.debug(f"FFmpeg: {line}")

            if self.stop_flag:
                break


async def process_video(
    stream_url: str, output_dir: str, m3u8_name: str, guide_id: str
) -> tuple:
    output_m3u8 = os.path.join(output_dir, m3u8_name)

    # Get correct stream url
    response = requests.get(stream_url, allow_redirects=True)
    redirected_url = response.url

    ffmpeg_params = {
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
