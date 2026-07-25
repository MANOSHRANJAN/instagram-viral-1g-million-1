"""Scroll an Instagram profile feed and surface the highest-engagement reels.

Composio's `instagram` toolkit is the Meta Graph API (your own account only).
For competitor scraping we use Firecrawl on the profile page, then sort by
visible engagement signals (likes/views) parsed from the rendered grid.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .composio_client import ComposioClient


_PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "handle": {"type": "string"},
        "bio": {"type": "string"},
        "follower_count": {"type": "integer"},
        "reels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "caption": {"type": "string"},
                    "views": {"type": "integer"},
                    "likes": {"type": "integer"},
                    "comments": {"type": "integer"},
                    "thumbnail_alt": {"type": "string"},
                },
                "required": ["url"],
            },
        },
    },
}


@dataclass
class IGProfile:
    handle: str
    bio: str = ""
    follower_count: int | None = None
    reels: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""


class IGScroller:
    def __init__(self, composio: ComposioClient):
        self.c = composio

    def scroll(self, handle_or_url: str, top_k: int = 5) -> IGProfile:
        url = self._to_url(handle_or_url)
        handle = self._handle_of(url)
        prof = IGProfile(handle=handle)
        if not self.c.is_connected("firecrawl"):
            prof.error = (
                "firecrawl not connected — run `python -m virality.cli auth firecrawl`"
            )
            return prof
        try:
            resp = self.c.execute(
                "FIRECRAWL_EXTRACT",
                {
                    "urls": [url, url + "reels/"],
                    "prompt": (
                        "Visit the Instagram profile and the /reels/ tab. "
                        "Return the handle, bio, follower count, and the visible reels "
                        "with their URL, caption, view count, like count, comment count, "
                        "and any visible alt text. Skip non-reel posts."
                    ),
                    "schema": _PROFILE_SCHEMA,
                    "enableWebSearch": False,
                },
                version=self.c.cfg.firecrawl_version,
            )
        except Exception as exc:
            prof.error = f"firecrawl error: {exc}"
            return prof
        data = ComposioClient.unwrap(resp) or {}
        payload: Any = data
        if isinstance(payload, dict) and "data" in payload:
            payload = payload["data"]
        if isinstance(payload, list) and payload:
            payload = payload[0]
        if not isinstance(payload, dict):
            prof.error = "firecrawl: unexpected shape"
            return prof
        prof.handle = str(payload.get("handle") or handle)
        prof.bio = str(payload.get("bio", ""))
        fc = payload.get("follower_count")
        prof.follower_count = int(fc) if isinstance(fc, (int, float)) else None
        reels = payload.get("reels") or []
        reels.sort(key=lambda r: (r.get("views") or 0) + (r.get("likes") or 0), reverse=True)
        prof.reels = reels[:top_k]
        return prof

    @staticmethod
    def _to_url(handle_or_url: str) -> str:
        s = handle_or_url.strip()
        if s.startswith("http"):
            return s if s.endswith("/") else s + "/"
        s = s.lstrip("@")
        return f"https://www.instagram.com/{s}/"

    @staticmethod
    def _handle_of(url: str) -> str:
        import re
        m = re.search(r"instagram\.com/([\w.\-]+)/?", url)
        return ("@" + m.group(1)) if m else ""
