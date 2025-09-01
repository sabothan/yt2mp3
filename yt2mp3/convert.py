from pathlib import Path
import os
import re
import sys
from typing import Optional
from tqdm import tqdm

# Cookie-enabled opener (works with pytubefix without a `cookies=` kwarg)
import http.cookiejar as cookiejar
from http.cookiejar import MozillaCookieJar
import urllib.request as urlreq
import urllib.error as urlerr

from pytubefix import YouTube, Playlist
from pytubefix import exceptions as yt_ex
import ffmpeg

# Allow disabling cookies via environment (helps avoid mixed-auth issues)
if os.environ.get("YT2MP3_NO_COOKIES") == "1":
    try:
        _reset_opener()
        print("[yt2mp3] Cookies disabled for this run (YT2MP3_NO_COOKIES=1).")
    except Exception:
        pass

# single-run verifier to avoid multiple device codes
_OAUTH_PROMPTED = False
def _oauth_verifier_once(verification_url: str, user_code: str):
    global _OAUTH_PROMPTED
    if not _OAUTH_PROMPTED:
        _OAUTH_PROMPTED = True
        print(f"Please open {verification_url} and input code {user_code}")
        input("Press Enter only after the page says authorization is complete.")
    else:
        print("[yt2mp3] OAuth is already in progress. Finish the FIRST device page — don’t request a new code.")
        input("When the first device page confirms authorization, press Enter here to continue.")

# -----------------------------
# Cookies: load once, package-local, and install opener
# -----------------------------
_DEFAULT_OPENER = urlreq.build_opener()
_COOKIE_OPENER_ACTIVE = False

def _install_cookie_opener(verbose: bool = False):
    """Install a global opener that carries cookies from yt2mp3/cookies/cookies.txt."""
    global _COOKIE_OPENER_ACTIVE
    cookie_path = Path(__file__).parent / "cookies" / "cookies.txt"
    if cookie_path.exists():
        try:
            cj = MozillaCookieJar(str(cookie_path))
            cj.load(ignore_discard=True, ignore_expires=True)
            handler = urlreq.HTTPCookieProcessor(cj)
            opener = urlreq.build_opener(handler)
            urlreq.install_opener(opener)
            _COOKIE_OPENER_ACTIVE = True
            if verbose:
                print(f"[yt2mp3] Using cookies from: {cookie_path}", flush=True)
        except Exception as e:
            print(f"Warning: Failed to load cookies at {cookie_path}: {e}", file=sys.stderr)

def _reset_opener():
    """Restore the default opener (no cookies)."""
    global _COOKIE_OPENER_ACTIVE
    urlreq.install_opener(_DEFAULT_OPENER)
    _COOKIE_OPENER_ACTIVE = False

# Global progress bar reference (one per download)
_CURRENT_PBAR = None

def _probe_audio_channels(path: Path) -> int:
    try:
        info = ffmpeg.probe(str(path))
        for s in info.get("streams", []):
            if s.get("codec_type") == "audio":
                ch = int(s.get("channels", 2) or 2)
                return max(1, min(ch, 8))
    except Exception:
        pass
    return 2

def _aac_bitrate_for_channels(ch: int) -> str:
    # Heuristic bitrates for AAC LC
    if ch >= 8:
        return "512k"
    if ch >= 6:
        return "384k"
    if ch >= 3:
        return "256k"
    return "192k"

def _slugify(title: str) -> str:
    # Replace OS-hostile characters; keep unicode
    title = re.sub(r'[\\/:*?"<>|]+', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title.rstrip('. ')

def _print(verbose: bool, *args, **kwargs):
    if verbose:
        print(*args, **kwargs, flush=True)

def _progress_cb(stream, chunk, bytes_remaining=None, **kwargs):
    """Compatible progress callback for pytube/pytubefix variants."""
    global _CURRENT_PBAR
    if _CURRENT_PBAR is None:
        return
    if bytes_remaining is None:
        bytes_remaining = kwargs.get('bytes_remaining', None)
        if bytes_remaining is None:
            return
    prev = getattr(stream, "_prev_remaining", None)
    if prev is None:
        setattr(stream, "_prev_remaining", bytes_remaining)
        processed = 0
    else:
        processed = max(0, prev - bytes_remaining)
        setattr(stream, "_prev_remaining", bytes_remaining)
    if processed:
        try:
            _CURRENT_PBAR.update(processed)
        except Exception:
            pass

def _best_video_stream(yt: YouTube):
    """Pick best adaptive MP4 video-only stream capped at 1440p/60fps."""
    def res_px(s):
        try:
            return int((s.resolution or "0p").rstrip("p"))
        except Exception:
            return 0
    def fps_val(s):
        try:
            return int(getattr(s, "fps", 0) or 0)
        except Exception:
            return 0
    base = yt.streams.filter(adaptive=True, only_video=True, subtype="mp4")
    capped = [s for s in base if res_px(s) <= 1440 and fps_val(s) <= 60]
    if capped:
        return sorted(capped, key=lambda s: (res_px(s), fps_val(s), getattr(s, "bitrate", 0)), reverse=True)[0]
    le1440 = [s for s in base if res_px(s) <= 1440]
    if le1440:
        return sorted(le1440, key=lambda s: (res_px(s), fps_val(s), getattr(s, "bitrate", 0)), reverse=True)[0]
    return base.order_by("resolution").desc().first()

def _best_audio_stream(yt: YouTube):
    # Prefer highest-abr audio-only regardless of mime (to allow opus/webm 5.1/7.1)
    stream = (yt.streams
                .filter(only_audio=True)
                .order_by("abr")
                .desc()
                .first())
    return stream

def _download_stream(stream, target: Path) -> Path:
    """Download a single pytube Stream to a path with a progress bar."""
    global _CURRENT_PBAR
    total = getattr(stream, "filesize", None) or getattr(stream, "filesize_approx", None) or 0
    try:
        _CURRENT_PBAR = tqdm(total=total, unit='B', unit_scale=True, desc=target.name)
        if hasattr(stream, "_prev_remaining"):
            delattr(stream, "_prev_remaining")
        stream.download(output_path=str(target.parent), filename=target.name)
    finally:
        if _CURRENT_PBAR is not None:
            _CURRENT_PBAR.close()
        _CURRENT_PBAR = None
    return target

def _mux_av(video_path: Path, audio_path: Path, out_path: Path, verbose: bool):
    ch = _probe_audio_channels(audio_path)
    abr = _aac_bitrate_for_channels(ch)
    _print(verbose, f"Muxing (H.264/AAC {ch}ch @ {abr}) -> {out_path.name}")
    v = ffmpeg.input(str(video_path))
    a = ffmpeg.input(str(audio_path))
    (
        ffmpeg
        .output(
            v, a, str(out_path),
            vcodec='libx264', acodec='aac',
            crf=18, preset='medium',
            pix_fmt='yuv420p',
            audio_bitrate=abr,
            ac=ch,
            movflags='use_metadata_tags+faststart',
            shortest=None
        )
        .overwrite_output()
        .run(quiet=not verbose)
    )

def _to_mp3(audio_path: Path, out_path: Path, verbose: bool):
    _print(verbose, f"Converting audio -> {out_path.name}")
    (
        ffmpeg
        .input(str(audio_path))
        .output(str(out_path), audio_bitrate='192k', acodec='libmp3lame', vn=None)
        .overwrite_output()
        .run(quiet=not verbose)
    )

def _download_video(yt: YouTube, out_dir: Path, verbose: bool, *, use_mkv: bool = False) -> Path:
    title = yt.title or "video"
    safe_title = _slugify(title)
    tmp_v = out_dir / f".tmp_{safe_title}.video"
    tmp_a = out_dir / f".tmp_{safe_title}.audio"
    ext = "mkv" if use_mkv else "mp4"
    out_path = out_dir / f"{safe_title}.{ext}"

    v_stream = _best_video_stream(yt)
    a_stream = _best_audio_stream(yt)
    if not v_stream or not a_stream:
        raise RuntimeError("No suitable video/audio stream found.")

    _print(verbose, f"Downloading video: {title}")
    _download_stream(v_stream, tmp_v)
    _print(verbose, f"Downloading audio")
    _download_stream(a_stream, tmp_a)

    if use_mkv:
        # Fast remux: no re-encode, just container copy
        _print(verbose, f"Muxing streams into MKV (no re-encode)")
        (
            ffmpeg
            .output(ffmpeg.input(str(tmp_v)), ffmpeg.input(str(tmp_a)), str(out_path),
                    c="copy", shortest=None)
            .overwrite_output()
            .run(quiet=not verbose)
        )
    else:
        # Re-encode to H.264/AAC MP4
        _mux_av(tmp_v, tmp_a, out_path, verbose)

    tmp_v.unlink(missing_ok=True)
    tmp_a.unlink(missing_ok=True)

    return out_path

def _download_audio(yt: YouTube, out_dir: Path, verbose: bool) -> Path:
    title = yt.title or "audio"
    safe_title = _slugify(title)
    tmp_a = out_dir / f".tmp_{safe_title}.audio"
    out_path = out_dir / f"{safe_title}.mp3"

    a_stream = _best_audio_stream(yt)
    if not a_stream:
        raise RuntimeError("No suitable audio stream found.")

    _print(verbose, f"Downloading audio for: {title}")
    _download_stream(a_stream, tmp_a)
    _to_mp3(tmp_a, out_path, verbose)
    try:
        tmp_a.unlink(missing_ok=True)
    except Exception:
        pass
    return out_path

def _process_single(url: str, out_dir: Path, *, download_video: bool, verbose: bool, use_mkv: bool = False) -> Path:
    def run_with(yt: YouTube):
        return _download_video(yt, out_dir, verbose, use_mkv=use_mkv) if download_video else _download_audio(yt, out_dir, verbose)

    # 1) Try anonymous first (cookies may help)
    try:
        yt = YouTube(url, on_progress_callback=_progress_cb)
        return run_with(yt)
    except yt_ex.AgeRestrictedError:
        if verbose:
            print("[yt2mp3] Age-restricted content detected — retrying with OAuth (cached)...", flush=True)
    except urlerr.HTTPError as he:
        if he.code == 400 and verbose:
            print("[yt2mp3] HTTP 400 during age check — retrying with OAuth (cached)...", flush=True)
        else:
            raise

    # Ensure cookies are NOT used during OAuth paths
    try:
        _reset_opener()
    except Exception:
        pass

    # 2) OAuth (cached token)
    try:
        yt = YouTube(url, on_progress_callback=_progress_cb, use_oauth=True, allow_oauth_cache=True)
        return run_with(yt)
    except (yt_ex.AgeRestrictedError, yt_ex.AgeCheckRequiredAccountError):
        if verbose:
            print("[yt2mp3] OAuth token insufficient — forcing fresh OAuth (no cache).", flush=True)
    except urlerr.HTTPError as he:
        if he.code == 400 and verbose:
            print("[yt2mp3] HTTP 400 with cached OAuth — forcing fresh OAuth (no cache).", flush=True)
        else:
            raise

    # 3) Fresh OAuth (single device prompt)
    yt = YouTube(
        url,
        on_progress_callback=_progress_cb,
        use_oauth=True,
        allow_oauth_cache=False,
        oauth_verifier=_oauth_verifier_once,
    )

    # After fresh auth: the token can take a moment to become usable.
    # Try immediately, then tolerate a few HTTP 428s with short waits.
    for attempt in range(5):  # 1 immediate + up to 4 retries
        try:
            return run_with(yt)
        except urlerr.HTTPError as he:
            if he.code == 428:
                wait = 3 + attempt * 2  # 3s,5s,7s,9s...
                if verbose:
                    print(f"[yt2mp3] OAuth just completed but token isn’t accepted yet (HTTP 428). Waiting {wait}s and retrying...", flush=True)
                time.sleep(wait)
                # after a short wait, use cached token
                yt = YouTube(url, on_progress_callback=_progress_cb, use_oauth=True, allow_oauth_cache=True)
                continue
            raise

def process_url(url: str, out_dir: Path, *, download_video: bool = False, verbose: bool = False):
    # Install cookie opener once per run (verbose output if requested)
    _install_cookie_opener(verbose=verbose)

    # Try playlist first
    try:
        pl = Playlist(url)
        if pl.video_urls:
            name = _slugify(pl.title or "playlist")
            playlist_dir = out_dir / name
            playlist_dir.mkdir(parents=True, exist_ok=True)
            print(f"Found playlist: {pl.title} ({len(pl.video_urls)} videos)")
            for idx, vid_url in enumerate(pl.video_urls, start=1):
                try:
                    result = _process_single(vid_url, playlist_dir, download_video=download_video, verbose=verbose)
                    print(f"[{idx}/{len(pl.video_urls)}] ✓ {result.name}")
                except Exception as e:
                    msg = str(e)
                    hint = ""
                    if ("age restricted" in msg.lower()) or ("sign in" in msg.lower()):
                        hint = "  (Tip: sign in with your primary Google account during the device flow; age verification may be required)"
                    print(f"[{idx}/{len(pl.video_urls)}] ✗ Failed: {e}{hint}")
            return
    except Exception:
        # Not a playlist; continue as single video
        pass

    # Single video
    try:
        result = _process_single(url, out_dir, download_video=download_video, verbose=verbose)
        print(f"✓ {result}")
    except Exception as e:
        msg = str(e)
        hint = ""
        if ("age restricted" in msg.lower()) or ("sign in" in msg.lower()):
            hint = "  (Tip: sign in with your primary Google account during the device flow; age verification may be required)"
        print(f"✗ Failed: {e}{hint}", file=sys.stderr)
        raise

