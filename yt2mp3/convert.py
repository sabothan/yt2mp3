import sys
import subprocess
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

from pytubefix import YouTube

from .helper import print_verbose

def convert(args):
    # Clean URL
    print_verbose("Sanitizing YouTube URL...", args.verbose)
    url = _clean_youtube_url(args.url)
    print_verbose(f"Using URL: `{url}`", args.verbose)

    # Prepare output directory
    out_dir = Path(args.path).expanduser().resolve()
    if not out_dir.exists():
        print_verbose(f"Output directory `{out_dir}` not found. Creating...", args.verbose)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        print_verbose(f"Output directory `{out_dir}` exists.", args.verbose)

    # Download audio stream
    print_verbose(f"Downloading audio from `{url}`", args.verbose)
    try:
        temp_path = _download_audio(url, out_dir)  # now returns a Path
    except Exception as e:
        print(f"Failed to download audio: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert to MP3
    mp3_name = temp_path.stem.replace("temp_", "") + ".mp3"
    mp3_path = out_dir / mp3_name
    print(f"Converting to MP3: `{mp3_name}`")
    try:
        _convert_to_mp3(temp_path, mp3_path, args.verbose)
    except Exception as e:
        print(f"Failed to convert to MP3: {e}", file=sys.stderr)
        sys.exit(1)

    # Clean up temporary files
    temp_path.unlink()
    print("Done!")

def _clean_youtube_url(url: str) -> str:
    """
    Strip out everything except the `v=...` query param so that pytube
    doesn’t choke on playlist/index parameters.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "v" not in qs:
        print("Error: URL does not contain a video ID (v=...).", file=sys.stderr)
        sys.exit(1)
    # Rebuild URL with only v=...
    new_qs = urlencode({"v": qs["v"][0]})
    cleaned = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_qs,
        ""  # no fragment
    ))
    return cleaned

def _download_audio(url: str, out_dir: Path) -> Path:
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

def _convert_to_mp3(src_path: Path, dest_path: Path, verbose: bool):
    """
    Invokes ffmpeg to transcode the downloaded file into an MP3.
    """
    if verbose:
        loglevel = "info"
    else:
        loglevel = "warning"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src_path),
        "-vn",             # no video
        "-ab", "192k",     # bitrate
        "-ar", "44100",    # sample rate
        "-loglevel", f"{loglevel}",
        str(dest_path)
    ]
    subprocess.run(cmd, check=True)
