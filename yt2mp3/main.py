import sys
import argparse

from .convert import convert
from .config import get_config, set_config


def main():
    parser = argparse.ArgumentParser(description="Convert YouTube videos to MP3.")
    subparser = parser.add_subparsers(dest="command", required=True)

    download = subparser.add_parser('download', description='Download audio from YouTube videos.')
    download.add_argument('url', type=str, help='The URL to the YouTube video')
    download.add_argument("-p", "--path", type=str, default=None, help="The target folder for the download. (Overrides config)")
    download.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    download.add_argument("--video", action="store_true", help="Download the entire video")
    
    config = subparser.add_parser('config', description='Configure the default values for the available flags')
    config.add_argument('option', type=str, help='Specify the option to configure')
    config.add_argument('value', type=str, help='Specify the value of the option to configure')

    args = parser.parse_args()

    if(args.command == 'download'):
        convert(args)

    elif(args.command == 'config'):
        set_config(key=args.option, value=args.value)


if __name__ == "__main__":
    main()
    sys.exit(0)
