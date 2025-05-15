import argparse

def main():
    parser = argparse.ArgumentParser(description='Convert YouTube videos to MP3.')
    parser.add_argument('--url', required=True, help='The URL to the YouTube video')
    parser.add_argument('--path', required=False, default='~/Downloads', help='The target folder for the download')

    args = parser.parse_args()

    print('Welcome to yt2mp3')

if __name__ == '__main__':
    main()
