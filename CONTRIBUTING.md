# Contributing to yt2mp3

Thanks for your interest in improving **yt2mp3**! 🎉  
This document explains how the project is structured, how to set up your environment, and the workflow we use for contributions.

---

## Project Overview

yt2mp3 is a command-line tool that wraps [pytubefix](https://github.com/pytube/pytube) + [ffmpeg](https://ffmpeg.org) to:

- Download audio or video from YouTube
- Handle playlists
- Re-encode video to H.264 MP4 (max 1440p/60fps)
- Re-encode audio to AAC (stereo / 5.1 / 7.1)
- Convert audio-only downloads to mp3
- Handle restricted content via cookies or OAuth
- Provide progress bars with `tqdm`

Core files:
- `main.py`: CLI entrypoint (argument parsing, dispatch)
- `convert.py`: core logic (stream selection, downloads, muxing, auth handling)
- `helper.py`: small utilities
- `config.py`: configuration defaults
- `requirements.txt`: dependencies

---

## Development Setup

### 1. Clone & environment
```bash
git clone https://github.com/yourname/yt2mp3.git
cd yt2mp3

# Create conda env (recommended)
conda create -n yt2mp3 python=3.9 -y
conda activate yt2mp3

# Install dependencies in editable mode
pip install -e .
```

### 2. Verify installation
Run:
```bash
yt2mp3 download "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --video -p ./out -v
```
You should see a progress bar and an `.mp4` in `./out`.

---

## Workflow for contributions

1. **Fork & branch**
   ```bash
   git checkout -b feature/playlist-enhancements
   ```

2. **Make changes**  
   For example, if you want to add a new CLI flag:
   - Add it in `main.py` (argparse).
   - Implement logic in `convert.py`.
   - Add helper functions in `helper.py` if needed.

3. **Test locally**
   ```bash
   yt2mp3 download "URL" --video -p ./out -v
   ```
   Validate:
   - Title-based filename is correct.
   - Progress bar works.
   - Resulting file opens in QuickTime.

4. **Lint & style**  
   We follow **PEP8**. Run:
   ```bash
   python -m flake8 yt2mp3
   ```

5. **Commit & push**
   ```bash
   git add .
   git commit -m "feat: added --max-fps option"
   git push origin feature/playlist-enhancements
   ```

6. **Open PR**  
   - Describe your changes clearly.
   - Reference issues if applicable.
   - Update `README.md` with new features.

---

## Example: Adding a new feature

Say we want a `--max-fps` option:

- **main.py**
  ```python
  dl.add_argument("--max-fps", type=int, default=60, help="Maximum FPS for video downloads")
  ```

- **convert.py**
  ```python
  def _best_video_stream(yt: YouTube, max_fps: int = 60):
      return yt.streams.filter(adaptive=True, only_video=True, subtype="mp4", fps__lte=max_fps).order_by("resolution").desc().first()
  ```

- **README.md**
  Update usage:
  ```bash
  yt2mp3 download "URL" --video --max-fps 30 -p ./out
  ```

- **Commit**
  ```bash
  git commit -m "feat: add --max-fps option for video downloads"
  ```

---

## Issues & PRs

- Please open an **issue** before working on large features.
- Small fixes and documentation improvements are welcome anytime.
- PRs should target the `main` branch.

---

Happy hacking 🚀  
If you build something cool with yt2mp3, share it!
