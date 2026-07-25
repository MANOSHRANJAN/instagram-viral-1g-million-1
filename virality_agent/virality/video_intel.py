"""Pull an Instagram reel's caption, transcript, engagement, AND watch it.

Two layers:
- Caption / engagement counts come from Firecrawl (Composio).
- The actual video is downloaded and watched: scene-change frames + a dense
  0-10s hook microscope. Frames feed the analyzer's vision call.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .composio_client import ComposioClient
from .watcher import ReelWatcher, WatchResult


@dataclass
class VideoFacts:
    url: str
    platform: str = "instagram"
    video_id: str = ""
    title: str = ""
    author: str = ""
    caption: str = ""
    transcript: str = ""
    duration_seconds: int | None = None
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    posted_at: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    watch: WatchResult | None = None

    def has_text(self) -> bool:
        return bool(self.transcript or self.caption)

    def has_visuals(self) -> bool:
        return bool(self.watch and (self.watch.hook_frames or self.watch.scene_frames))


_FC_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "author": {"type": "string", "description": "Instagram handle that posted the reel."},
        "caption": {"type": "string", "description": "The post caption text."},
        "transcript": {"type": "string", "description": "Spoken or on-screen words from the reel."},
        "views": {"type": "integer"},
        "likes": {"type": "integer"},
        "comments": {"type": "integer"},
        "posted_at": {"type": "string"},
    },
}


class VideoIntel:
    def __init__(self, composio: ComposioClient, watch: bool = True):
        self.c = composio
        self._watch = watch and composio.cfg.watch_reels
        self._watcher = (
            ReelWatcher(
                cookies_file=composio.cfg.ig_cookies_file or None,
                chrome_profile=composio.cfg.ig_chrome_profile,
            )
            if self._watch
            else None
        )

    def fetch(self, url: str) -> VideoFacts:
        if "instagram.com" not in url.lower():
            return VideoFacts(
                url=url,
                error="virality_agent is Instagram-only. Pass an instagram.com/reel/... URL.",
            )
        facts = self._fetch_via_firecrawl(url)
        if self._watch and self._watcher:
            try:
                wr = self._watcher.watch(url)
                facts.watch = wr
                if wr.duration_seconds:
                    facts.duration_seconds = int(wr.duration_seconds)
            except Exception as exc:
                facts.watch = WatchResult(error=f"watcher crashed: {exc}")
        return facts

    def _fetch_via_firecrawl(self, url: str) -> VideoFacts:
        facts = VideoFacts(url=url, video_id=_reel_id(url))
        if not self.c.is_connected("firecrawl"):
            # Not fatal anymore — the watcher path can still see visuals.
            facts.error = "firecrawl not connected (caption/engagement unavailable)"
            return facts
        try:
            resp = self.c.execute(
                "FIRECRAWL_EXTRACT",
                {
                    "urls": [url],
                    "prompt": (
                        "Extract the Instagram reel's author handle, caption, "
                        "spoken/on-screen transcript, views, likes, and comments. "
                        "Use empty values if a field is not visible."
                    ),
                    "schema": _FC_SCHEMA,
                    "enableWebSearch": False,
                },
                version=self.c.cfg.firecrawl_version,
            )
        except Exception as exc:
            facts.error = f"firecrawl error: {exc}"
            return facts
        data = ComposioClient.unwrap(resp) or {}
        payload: Any = data
        if isinstance(payload, dict) and "data" in payload:
            payload = payload["data"]
        if isinstance(payload, list) and payload:
            payload = payload[0]
        if not isinstance(payload, dict):
            facts.error = "firecrawl: unexpected response shape"
            facts.raw = {"resp": str(data)[:400]}
            return facts
        facts.title = str(payload.get("title", ""))
        facts.author = str(payload.get("author", ""))
        facts.caption = str(payload.get("caption", ""))
        facts.transcript = str(payload.get("transcript", ""))
        facts.views = _to_int(payload.get("views"))
        facts.likes = _to_int(payload.get("likes"))
        facts.comments = _to_int(payload.get("comments"))
        facts.posted_at = str(payload.get("posted_at", ""))
        facts.raw = payload
        return facts


def _reel_id(url: str) -> str:
    m = re.search(r"/reel/([^/?]+)", url) or re.search(r"/p/([^/?]+)", url)
    return m.group(1) if m else ""


def _to_int(v: Any) -> int | None:
    if v is None or v == "":
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip().lower().replace(",", "")
    m = re.match(r"([\d.]+)\s*([kmb]?)", s)
    if not m:
        return None
    num = float(m.group(1))
    suffix = m.group(2)
    return int(num * {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(suffix, 1))
