#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

from .download import download_audio, convert_to_mp3
from .config import get_config, set_config

def clean_youtube_url(url: str) -> str:
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

def print_verbose(msg: str, verbose: bool):
    if verbose:
        print(msg)

def main():
    parser = argparse.ArgumentParser(description="Convert YouTube videos to MP3.")
    subparser = parser.add_subparsers(dest="command", required=True)

    
    download = subparser.add_parser('download', description='Download audio from YouTube videos.')
    # download.add_argument("-u", "--url",
    #                     required=True,
    #                     help="The URL to the YouTube video")
    download.add_argument('url', nargs='*', help='The URL to the YouTube video')
    download.add_argument("-p", "--path",
                        default="~/Downloads",
                        help="The target folder for the download")
    download.add_argument("-v", "--verbose",
                        action="store_true",
                        help="Enable verbose output")
    
    config = subparser.add_parser('config', description='Configure the default values for the available flags')
    config.add_argument('option', nargs='+', help='Specify the option to configure')
    config.add_argument('value', nargs='+', help='Specify the value of the option to configure')

    args = parser.parse_args()

    if(args.command == 'download'):
        # Clean URL
        print_verbose("Sanitizing YouTube URL...", args.verbose)
        url = clean_youtube_url(args.url)
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
            temp_path = download_audio(url, out_dir)  # now returns a Path
        except Exception as e:
            print(f"Failed to download audio: {e}", file=sys.stderr)
            sys.exit(1)

        # Convert to MP3
        mp3_name = temp_path.stem.replace("temp_", "") + ".mp3"
        mp3_path = out_dir / mp3_name
        print(f"Converting to MP3: `{mp3_name}`")
        try:
            convert_to_mp3(temp_path, mp3_path, args.verbose)
        except Exception as e:
            print(f"Failed to convert to MP3: {e}", file=sys.stderr)
            sys.exit(1)

        # Clean up temporary files
        temp_path.unlink()
        print("Done!")

    elif(args.command == 'config'):
        set_config(key=args.option, value=args.value)


if __name__ == "__main__":
    main()
