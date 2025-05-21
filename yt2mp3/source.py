import sys
import subprocess
from pathlib import Path
from urllib.error import HTTPError

from pytubefix import YouTube
from pytubefix.cli import on_progress  # optional, if you want callbacks

def download_audio(url: str, out_dir: Path) -> Path:
    """
    Downloads the highest-quality audio stream to `out_dir`, 
    prefixed with "temp_". Returns the full Path to the downloaded file.
    """
    try:
        yt = YouTube(url)
    except HTTPError as err:
        raise RuntimeError(f"HTTP error from YouTube: {err.code}") from err

    stream = (
        yt.streams
          .filter(only_audio=True)
          .order_by('abr')
          .last()
    )
    if not stream:
        raise RuntimeError("No audio streams found for this video.")

    out_file = stream.download(
        output_path=str(out_dir),
        filename_prefix="temp_"
    )
    return Path(out_file)

def convert_to_mp3(src_path: Path, dest_path: Path):
    """
    Invokes ffmpeg to transcode the downloaded file into an MP3.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src_path),
        "-vn",             # no video
        "-ab", "192k",     # bitrate
        "-ar", "44100",    # sample rate
        "-loglevel", "warning",
        str(dest_path)
    ]
    subprocess.run(cmd, check=True)
