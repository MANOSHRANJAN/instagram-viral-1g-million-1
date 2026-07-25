"""Watch an Instagram reel — download, extract scene-change frames,
densely sample the 0-10s hook, transcribe.

This is the native port of the `claude-watch` skill, tuned for IG reels:
- yt-dlp downloads the .mp4
- ffmpeg scene-detect grabs one frame per cut (flat token cost on long reels)
- ffmpeg dense-samples the first 10s at 2 fps (the hook microscope)
- ffmpeg extracts audio for whisper-based transcription (optional)
"""
from __future__ import annotations

import base64
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import mkdtemp


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


@dataclass
class WatchResult:
    video_path: str = ""
    duration_seconds: float = 0.0
    scene_frames: list[str] = field(default_factory=list)   # paths to PNGs at scene cuts
    hook_frames: list[str] = field(default_factory=list)    # paths to PNGs in 0-10s
    audio_path: str = ""
    transcript: str = ""
    error: str = ""

    def all_frames(self, max_total: int = 12) -> list[str]:
        """Return a deduped, capped list of frames for the vision prompt.

        Hook frames go first (most important), then scene frames.
        """
        seen, out = set(), []
        for p in self.hook_frames + self.scene_frames:
            if p in seen:
                continue
            seen.add(p)
            out.append(p)
            if len(out) >= max_total:
                break
        return out


class ReelWatcher:
    """Downloads a reel and extracts visual + audio context."""

    def __init__(
        self,
        scene_threshold: float = 0.30,
        hook_seconds: float = 10.0,
        hook_fps: float = 2.0,
        max_duration: float = 120.0,
        cookies_from_browser: str | None = "chrome",
        chrome_profile: str | None = None,
        cookies_file: str | None = None,
        download_timeout: int = 300,
    ):
        self.scene_threshold = scene_threshold
        self.hook_seconds = hook_seconds
        self.hook_fps = hook_fps
        self.max_duration = max_duration
        self.cookies_from_browser = cookies_from_browser
        self.chrome_profile = chrome_profile
        self.cookies_file = cookies_file
        self.download_timeout = download_timeout

    def watch(self, url: str, workdir: Path | None = None) -> WatchResult:
        if not _have("ffmpeg"):
            return WatchResult(error="ffmpeg not found. Install with: brew install ffmpeg")
        if not _have("yt-dlp"):
            return WatchResult(error="yt-dlp not found. Install with: brew install yt-dlp")

        workdir = workdir or Path(mkdtemp(prefix="virality_watch_"))
        workdir.mkdir(parents=True, exist_ok=True)
        video_path = workdir / "reel.mp4"

        # 1) Download — Instagram blocks anonymous downloads, so we pass cookies
        cmd = [
            "yt-dlp",
            "--quiet",
            "--no-warnings",
            "-f", "mp4/best[ext=mp4]/best",
            "-o", str(video_path),
        ]
        if self.cookies_file:
            cmd += ["--cookies", self.cookies_file]
        elif self.cookies_from_browser:
            spec = self.cookies_from_browser
            if self.cookies_from_browser == "chrome" and self.chrome_profile:
                spec = f"chrome:{self.chrome_profile}"
            cmd += ["--cookies-from-browser", spec]
        cmd.append(url)

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=self.download_timeout)
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or b"").decode("utf-8", errors="ignore")[:400]
            hint = ""
            if "empty media response" in stderr or "login required" in stderr.lower():
                hint = (
                    "\nFix: log in to instagram.com in Chrome (or Safari/Firefox), "
                    "then re-run. The watcher reads cookies from your browser."
                )
            return WatchResult(error=f"yt-dlp failed: {stderr}{hint}")
        except subprocess.TimeoutExpired:
            return WatchResult(
                error=f"yt-dlp timed out ({self.download_timeout}s). "
                "If you have many Chrome profiles, set IG_CHROME_PROFILE env var "
                "(e.g. 'Default') to pin one."
            )

        if not video_path.exists() or video_path.stat().st_size < 1024:
            return WatchResult(error="downloaded file missing or too small")

        result = WatchResult(video_path=str(video_path))
        result.duration_seconds = self._duration(video_path)

        # 2) Hook microscope: dense 0-10s sampling
        hook_dir = workdir / "hook"
        hook_dir.mkdir(exist_ok=True)
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-t", str(self.hook_seconds),
                    "-i", str(video_path),
                    "-vf", f"fps={self.hook_fps},scale=480:-1",
                    str(hook_dir / "hook_%03d.jpg"),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
            result.hook_frames = sorted(str(p) for p in hook_dir.glob("hook_*.jpg"))
        except subprocess.CalledProcessError as exc:
            result.error = f"hook frames failed: {(exc.stderr or b'').decode()[:200]}"

        # 3) Scene-change frames across the rest
        scene_dir = workdir / "scenes"
        scene_dir.mkdir(exist_ok=True)
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-i", str(video_path),
                    "-vf", f"select='gt(scene,{self.scene_threshold})',scale=480:-1",
                    "-vsync", "vfr",
                    str(scene_dir / "scene_%03d.jpg"),
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
            result.scene_frames = sorted(str(p) for p in scene_dir.glob("scene_*.jpg"))
        except subprocess.CalledProcessError as exc:
            # not fatal — short reels may have no detected cuts
            pass

        # 4) Audio (for caller-side whisper if they want it)
        audio_path = workdir / "audio.mp3"
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-i", str(video_path),
                    "-vn", "-ac", "1", "-ar", "16000",
                    "-b:a", "64k",
                    str(audio_path),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
            result.audio_path = str(audio_path)
        except subprocess.CalledProcessError:
            pass

        return result

    def _duration(self, path: Path) -> float:
        try:
            out = subprocess.check_output(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                timeout=15,
            )
            return float(out.strip() or 0)
        except Exception:
            return 0.0


def frame_to_b64(path: str) -> str:
    """JPEG file → base64 string for an Anthropic vision message."""
    return base64.standard_b64encode(Path(path).read_bytes()).decode("ascii")


def transcribe_with_groq(audio_path: str, api_key: str) -> str:
    """Optional: hit Groq's whisper-large-v3 endpoint. Returns text or ''."""
    if not audio_path or not Path(audio_path).exists():
        return ""
    try:
        import httpx  # already a transitive dep of anthropic
    except ImportError:
        return ""
    try:
        with open(audio_path, "rb") as f:
            r = httpx.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data={"model": "whisper-large-v3", "response_format": "json"},
                files={"file": (Path(audio_path).name, f, "audio/mpeg")},
                timeout=60.0,
            )
        if r.status_code == 200:
            return r.json().get("text", "")
    except Exception:
        pass
    return ""
