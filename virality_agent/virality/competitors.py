"""Find competitors and their best-performing AI-niche videos.

Uses Exa for discovery (real search across YouTube/Instagram/TikTok)
and falls back to a curated seed list if Exa isn't connected yet.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .composio_client import ComposioClient


SEED_AI_CREATORS = [
    "https://www.instagram.com/heyriley/",
    "https://www.instagram.com/aiwarper/",
    "https://www.instagram.com/aitechtips/",
    "https://www.instagram.com/futurepedia_io/",
    "https://www.instagram.com/theaibreakdown/",
    "https://www.instagram.com/ai.with.adam/",
    "https://www.instagram.com/benlatz.ai/",
    "https://www.instagram.com/gpt.minds/",
]


@dataclass
class Competitor:
    handle: str
    platform: str
    profile_url: str
    notes: str = ""
    sample_videos: list[str] = field(default_factory=list)


class CompetitorScout:
    def __init__(self, composio: ComposioClient):
        self.c = composio

    def discover(self, niche: str = "ai automation tools", n: int = 10) -> list[Competitor]:
        if not self.c.is_connected("exa"):
            return self._seed()
        try:
            resp = self.c.execute(
                "EXA_SEARCH",
                {
                    "query": f"{niche} viral instagram reel creator",
                    "numResults": n,
                    "includeDomains": ["instagram.com"],
                    "contents": {"highlights": True},
                },
                version=self.c.cfg.exa_version,
            )
        except Exception as exc:
            return self._seed(note=f"exa fallback: {exc}")
        data = ComposioClient.unwrap(resp)
        results = (data or {}).get("results") if isinstance(data, dict) else None
        if not results:
            return self._seed()
        out: list[Competitor] = []
        for r in results:
            url = r.get("url", "")
            platform = self._platform_of(url)
            handle = self._handle_of(url)
            if not handle:
                continue
            out.append(Competitor(
                handle=handle,
                platform=platform,
                profile_url=url,
                notes=(r.get("title") or "")[:140],
            ))
        return out or self._seed()

    @staticmethod
    def _platform_of(url: str) -> str:
        u = url.lower()
        if "youtube.com" in u or "youtu.be" in u:
            return "youtube"
        if "instagram.com" in u:
            return "instagram"
        if "tiktok.com" in u:
            return "tiktok"
        return "web"

    @staticmethod
    def _handle_of(url: str) -> str:
        m = re.search(r"@([\w.\-]+)", url)
        if m:
            return "@" + m.group(1)
        m = re.search(r"instagram\.com/([\w.\-]+)/?", url)
        if m and m.group(1) not in ("p", "reel", "reels", "tv"):
            return "@" + m.group(1)
        m = re.search(r"tiktok\.com/@([\w.\-]+)", url)
        if m:
            return "@" + m.group(1)
        return ""

    @staticmethod
    def _seed(note: str = "") -> list[Competitor]:
        out = []
        for url in SEED_AI_CREATORS:
            out.append(Competitor(
                handle=CompetitorScout._handle_of(url),
                platform=CompetitorScout._platform_of(url),
                profile_url=url,
                notes=note or "seed list",
            ))
        return out
