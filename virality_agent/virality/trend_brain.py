"""The Brain — finds today's most viral-worthy AI topics and clones the pattern
into ready-to-shoot reel scripts in your voice.

Pipeline:
1. Pull fresh headlines from Google News RSS (free, no auth) across AI queries.
2. Rank by recency + how many sources cover it (frequency = it's actually hot).
3. Feed the top stories to your Kiro LLM: pick the most viral-worthy, reverse-
   engineer WHY it works, and write a 30s reel script in your style.
"""
from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import requests

from .config import Config
from .llm import LLMClient
from .analyzer import _extract_json

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) trend-brain/1.0"

# Queries tuned to the niche: AI, tools, automation, agents + the money/biz angle.
DEFAULT_QUERIES = [
    "AI agents", "AI automation", "ChatGPT OR OpenAI", "new AI tool",
    "AI replacing jobs", "AI for small business", "Claude AI", "AI startup",
]


@dataclass
class Story:
    title: str
    source: str = ""
    link: str = ""
    published: datetime | None = None
    hits: int = 1
    queries: set[str] = field(default_factory=set)


def _norm(title: str) -> str:
    t = html.unescape(title or "").lower()
    t = re.sub(r"\s*-\s*[^-]+$", "", t)  # strip trailing " - Source"
    t = re.sub(r"[^a-z0-9 ]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def fetch_headlines(queries: list[str], per_query: int = 12) -> list[Story]:
    merged: dict[str, Story] = {}
    for q in queries:
        url = "https://news.google.com/rss/search"
        params = {"q": f"{q} when:2d", "hl": "en-US", "gl": "US", "ceid": "US:en"}
        try:
            r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=20)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
        except Exception:
            continue
        for item in list(root.iterfind(".//item"))[:per_query]:
            title = (item.findtext("title") or "").strip()
            if not title:
                continue
            link = (item.findtext("link") or "").strip()
            src_el = item.find("{*}source") or item.find("source")
            source = (src_el.text if src_el is not None else "") or ""
            pub = item.findtext("pubDate")
            try:
                published = parsedate_to_datetime(pub) if pub else None
            except Exception:
                published = None
            key = _norm(title)
            if not key:
                continue
            if key in merged:
                merged[key].hits += 1
                merged[key].queries.add(q)
            else:
                merged[key] = Story(title=html.unescape(title), source=source,
                                    link=link, published=published, queries={q})
        time.sleep(0.4)
    return list(merged.values())


def rank_stories(stories: list[Story], limit: int = 20) -> list[Story]:
    now = datetime.now(timezone.utc)

    def score(s: Story) -> float:
        recency = 0.0
        if s.published:
            hrs = max(1.0, (now - s.published.astimezone(timezone.utc)).total_seconds() / 3600)
            recency = max(0.0, 48 - hrs)  # newer = higher, 0 after 48h
        return s.hits * 10 + recency  # cross-source coverage dominates

    return sorted(stories, key=score, reverse=True)[:limit]


BRAIN_SYSTEM = (
    "You are a viral short-form content strategist. You read today's real news headlines, "
    "identify which stories will make the most viral Instagram Reels for a specific creator, "
    "reverse-engineer WHY, and write ready-to-shoot 30-second scripts. Return ONLY valid JSON."
)

BRAIN_PROMPT = """Creator: Manosh — founder of TheClientPilot, an AI automation agency that builds
AI receptionists/chatbots for dental clinics & service businesses. He posts about AI, new
tools, and automation. Voice: blunt, energetic, Gen-Z-punchy, no fluff. Audience: business
owners, founders, and anyone AI-curious. Goal: maximum reach + saves, then convert to agency leads.

Below are REAL headlines from the last 2 days (title | source | how many outlets covered it).
Pick the {n} MOST viral-worthy for his audience. For each, write a ready reel.

HEADLINES:
{headlines}

Return ONLY this JSON:
{{
  "picks": [
    {{
      "topic": "the story in plain words",
      "why_viral": "why THIS will pop right now (recency, emotion, stakes, relatability)",
      "pillar": "AI Shifts | Tool Breakdown | Hot Take | Proof | Founder",
      "hook": "0-2s scroll-stopping opening line, spoken",
      "script": "full ~30s / ~70-word talking-head script in his voice, with line breaks",
      "onscreen_text": ["3-5 burned-in caption phrases"],
      "cta": "one-line CTA ending in a keyword like BOND",
      "caption": "IG caption with 4-6 hashtags"
    }}
  ]
}}
"""


def analyze_and_script(cfg: Config, stories: list[Story], n: int = 5) -> dict:
    llm = LLMClient(cfg)
    if not llm.available():
        raise RuntimeError("No LLM backend available (set KIRO_API_KEY).")
    lines = []
    for s in stories:
        cov = f"{s.hits} outlet(s)"
        lines.append(f"- {s.title} | {s.source or '?'} | {cov}")
    prompt = BRAIN_PROMPT.format(n=n, headlines="\n".join(lines))
    out = llm.complete(system=BRAIN_SYSTEM, user=prompt, max_tokens=3500)
    return _extract_json(out)


def run(cfg: Config, queries: list[str] | None = None, n: int = 5) -> tuple[list[Story], dict]:
    stories = rank_stories(fetch_headlines(queries or DEFAULT_QUERIES))
    picks = analyze_and_script(cfg, stories, n=n)
    return stories, picks
