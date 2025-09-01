#!/usr/bin/env python3
import argparse
from pathlib import Path
from .convert import process_url

def build_parser():
    p = argparse.ArgumentParser(
        prog="yt2mp3",
        description="Download audio (MP3) or video (MP4) from YouTube URLs or playlists."
    )
    sub = p.add_subparsers(dest="command", required=True)

    dl = sub.add_parser("download", help="Download from a YouTube URL or playlist")
    dl.add_argument("url", type=str, help="YouTube video or playlist URL")
    dl.add_argument("-p", "--path", type=str, default=str(Path.home() / "Downloads"),
                    help="Target output directory (default: ~/Downloads)")
    dl.add_argument("--video", action="store_true",
                    help="Download best video + best audio and mux (MP4). Default is MP3 audio only.")
    dl.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    dl.add_argument("--mkv", action="store_true",
                    help="Save as MKV without re-encoding (fast, lossless, but not QuickTime compatible)")
    return p

def main():
    args = build_parser().parse_args()
    if args.command == "download":
        out_dir = Path(args.path).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        process_url(args.url, out_dir, download_video=args.video, verbose=args.verbose, use_mkv=args.mkv)

if __name__ == "__main__":
    main()
