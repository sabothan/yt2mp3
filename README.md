# `yt2mp3` - YouTube to MP3 Downloader

The project `yt2mp3` represents a simple command line interface (CLI)
that converts YouTube videos to MP3 files and downloads them to your
machine.

Usage: 
```bash
yt2mp3 [options]
```

Available `[options]`:
- `--url`, `-u`: The YouTube URL as a `str`. **REQUIRED**
- `--path`, `-p`: The target folder, where the audio file lands. Defaults to `~/Downloads` **OPTIONAL**
- `--verbose`, `-v`: `Show verbose output. **OPTIONAL**

Example:

```bash
yt2mp3 --url "https://www.youtube.com/watch?v=z1Dv_MOP6-Q" --path ~/Downloads/test -v
```