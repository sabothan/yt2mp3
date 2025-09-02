# yt2mp3

A simple CLI tool to download YouTube videos or audio.  
Supports playlists, title-based filenames, progress bars, and automatic handling of age-restricted videos.

---

## Features
- Download **audio (mp3)** or **video (mp4)** from YouTube
- Playlist support (downloads into a subfolder named after the playlist)
- Automatic **title-based filenames**
- **1440p / 60fps max cap** for video (H.264 re-encode for compatibility)
- Preserves **multichannel audio (stereo / 5.1 / 7.1)** in AAC
- Progress bars for downloads
- Age-restricted/private videos:
  - Uses `yt2mp3/cookies/cookies.txt` automatically if present
  - Falls back to OAuth device login when cookies are insufficient

---

## Installation

### With conda (recommended)
```bash
conda create -n yt2mp3 python=3.9 -y
conda activate yt2mp3
pip install -e .
```

### With pip
```bash
pip install -e .
```

Dependencies are listed in `requirements.txt`.

---

## Usage

Download audio (mp3):
```bash
yt2mp3 download "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -p ~/Downloads
```

Download video (mp4, capped at 1440p/60fps):
```bash
yt2mp3 download "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --video -p ~/Downloads
```

Download a playlist:
```bash
yt2mp3 download "https://www.youtube.com/playlist?list=XXXXXXXX" --video -p ~/Downloads
```

Verbose mode (shows detailed logs):
```bash
yt2mp3 download "URL" --video -p ~/Downloads -v
```

**Note**:  
When downloading a video `--video` by default a `.mp4` file will be generated. If you wish to get a `.mkv` instead simply pass the flag `--mkv` to the CLI call.



---

## Handling age-restricted content

### Cookies
Export your YouTube cookies in **Netscape format** and save them as:
```
yt2mp3/cookies/cookies.txt
```
They will be applied automatically.

### OAuth fallback
If cookies are missing or insufficient, yt2mp3 will fall back to OAuth:
- It will display a device login URL + code.
- Open the link in an **incognito/private window**.
- Log in with your **primary Google account** and enter the code.
- Wait until the page says “Access granted”.
- Then return to the terminal and press Enter.

Tokens are cached for future runs.

---

## License
MIT
