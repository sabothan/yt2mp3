import sys
import subprocess
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

from pytubefix import YouTube
from pytubefix.cli import on_progress

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

    # Check whether the audio should be downloaded or the video
    if(args.video is True):
        # Download video stream
        print_verbose(f"Downloading video from `{url}`", args.verbose)
        try:
            video_file, audio_file, video_name = _download_video(url, out_dir)
        except Exception as e:
            print(f"Failed to download video: {e}", file=sys.stderr)
            sys.exit(1)

        # Merge audio and video
        print_verbose(f"Muxing audio and video files: `{video_name}`", args.verbose)
        _merge_audio_video(
            video_name=video_name,
            audio_file=audio_file,
            video_file=video_file,
            dest_path=out_dir,
            verbose=args.verbose,
        )

        # cleanup temp files
        video_file.unlink()
        audio_file.unlink()

    else:
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
        print_verbose(f"Converting to MP3: `{mp3_name}`", args.verbose)
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

def _download_video(url: str, out_dir: Path) -> tuple[Path, Path, str]:
    """
    Downloads the highest-quality video stream to `out_dir`
    """
    try:
        yt = YouTube(url, on_progress_callback=on_progress)
    except HTTPError as err:
        raise RuntimeError(f"HTTP error from YouTube: {err.code}") from err

    # 1) Highest-res video-only
    video_stream = yt.streams.filter(adaptive=True, only_video=True)
    video_name = f"{yt.video_id}.mp4"

    # 1.1) Retrieve resolutions below 1440p
    capped = []
    for s in video_stream:
        if s.resolution is None:
            continue
        # strip 'p' and convert to int
        res = int(s.resolution.rstrip("p"))
        if res <= 1440:
            capped.append((res, s))
    if not capped:
        raise RuntimeError("No video-only streams at 1440p or below found.") 

     # 1.2) Pick the one with the highest resolution ≤1440p
    _, video_stream = max(capped, key=lambda tup: tup[0])

    # 2) Best audio-only
    audio_stream = (
        yt.streams
          .filter(adaptive=True, only_audio=True)
          .order_by("abr")
          .last()
    )
    if not audio_stream:
        raise RuntimeError("No audio-only streams found.")

    # 3) Download both
    video_file = video_stream.download(
        output_path=str(out_dir), 
        filename_prefix="vid_"
    )
    audio_file = audio_stream.download(
        output_path=str(out_dir), 
        filename_prefix="aud_"
    )

    return Path(video_file), Path(audio_file), video_name


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

def _merge_audio_video(video_name: str, audio_file: Path, video_file: Path, dest_path: Path, verbose: bool):
    """
    Merge/mux the seperated audio and video files into an mp4 video file.
    """
    if verbose:
        loglevel = "info"
    else:
        loglevel = "warning"   

    final_path = dest_path / video_name
    cmd = [
        "ffmpeg", "-loglevel", f"{loglevel}", "-y",
        "-i", str(video_file),
        "-i", str(audio_file),
        # copy video stream, transcode audio to AAC
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        # ensure we map exactly one video and one audio
        "-map", "0:v:0",
        "-map", "1:a:0",
        str(final_path)
    ]
    subprocess.run(cmd, check=True)

