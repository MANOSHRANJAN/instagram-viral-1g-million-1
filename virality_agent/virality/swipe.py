"""Swipe File — a dashboard of proven viral short-form videos, reverse-engineered.

Store real 1M+ view videos with their hook, transcript, CTA, format and WHY they
worked. Ingest pulls real data (views + auto-captions) via yt-dlp — no guesswork.
Then `analyze` uses your Kiro LLM to extract the repeatable patterns.

Data lives in content/swipe_file.json.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .config import Config
from .llm import LLMClient
from .analyzer import _extract_json


def _store_path() -> Path:
    # content/ lives at the workspace root (parent of the package's parent)
    root = Path(__file__).resolve().parent.parent.parent
    p = root / "content" / "swipe_file.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_store() -> list[dict[str, Any]]:
    p = _store_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except Exception:
        return []


def save_store(entries: list[dict[str, Any]]) -> Path:
    p = _store_path()
    p.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    return p


@dataclass
class Swipe:
    url: str = ""
    creator: str = ""
    platform: str = ""
    views: int = 0
    hook: str = ""
    transcript: str = ""
    cta: str = ""
    format: str = ""
    niche: str = ""
    why_it_worked: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


# ---------- yt-dlp ingest (real data) ----------

def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _parse_vtt(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s == "WEBVTT" or "-->" in s or s.isdigit():
            continue
        if s.startswith(("Kind:", "Language:", "NOTE")):
            continue
        s = re.sub(r"<[^>]+>", "", s)  # strip timing tags
        if s and (not lines or lines[-1] != s):
            lines.append(s)
    # dedupe consecutive repeats common in auto-subs
    out: list[str] = []
    for s in lines:
        if not out or out[-1].lower() != s.lower():
            out.append(s)
    return " ".join(out)


def _cookie_args(cfg: Config, url: str) -> list[str]:
    """Instagram/TikTok need login cookies. Use a cookies file if set, else the browser."""
    low = url.lower()
    if not any(s in low for s in ("instagram.com", "tiktok.com", "facebook.com")):
        return []
    if getattr(cfg, "ig_cookies_file", ""):
        return ["--cookies", cfg.ig_cookies_file]
    spec = "chrome"
    prof = getattr(cfg, "ig_chrome_profile", "") or ""
    if prof:
        spec = f"chrome:{prof}"
    return ["--cookies-from-browser", spec]


def ingest_url(cfg: Config, url: str) -> Swipe:
    """Pull real metadata + transcript via yt-dlp. Works on Instagram reels (with
    login cookies), TikTok, and YouTube. IG reels have no caption track, so we
    transcribe the audio when a transcription key is available."""
    sw = Swipe(url=url)
    cookies = _cookie_args(cfg, url)
    is_ig = "instagram.com" in url.lower()

    # 1) metadata (views, creator, caption in description)
    caption = ""
    try:
        meta = _run(["yt-dlp", "--dump-single-json", "--skip-download", "--no-warnings", *cookies, url])
        if meta.returncode == 0 and meta.stdout.strip():
            j = json.loads(meta.stdout)
            sw.creator = j.get("uploader") or j.get("channel") or j.get("uploader_id") or ""
            sw.views = int(j.get("view_count") or j.get("like_count") or 0)
            sw.platform = (j.get("extractor_key") or "").lower()
            caption = j.get("description") or j.get("title") or ""
            sw.cta = _guess_cta(caption)
        else:
            err = (meta.stderr or "")[:200]
            if is_ig and ("login" in err.lower() or "cookies" in err.lower() or "rate" in err.lower()):
                sw.why_it_worked = "[ingest note] Instagram needs login — log into instagram.com in Chrome, then retry."
    except Exception:
        pass

    # 2) transcript
    #    Preferred: Composio Supadata (works for IG/TikTok/YT, no cookies).
    #    Fallbacks: YouTube auto-captions (vtt) → audio transcription (Groq).
    sw.transcript = supadata_transcript(cfg, url)
    got_subs = bool(sw.transcript)
    if not got_subs:
        try:
            with tempfile.TemporaryDirectory() as td:
                tmpl = str(Path(td) / "sub")
                _run([
                    "yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs",
                    "--sub-langs", "en.*", "--sub-format", "vtt", "--no-warnings",
                    *cookies, "-o", tmpl, url,
                ])
                vtts = list(Path(td).glob("*.vtt"))
                if vtts:
                    sw.transcript = _parse_vtt(vtts[0].read_text(errors="ignore"))[:6000]
                    got_subs = True
        except Exception:
            pass

    if not got_subs:
        # last resort: download audio + transcribe (IG/TikTok, needs GROQ_API_KEY)
        transcribed = _download_and_transcribe(cfg, url, cookies)
        if transcribed:
            sw.transcript = transcribed[:6000]

    # 3) hook = spoken opening, else caption's first line
    if sw.transcript:
        sw.hook = " ".join(sw.transcript.split()[:14])
    elif caption:
        sw.hook = caption.strip().splitlines()[0][:140]
        if not sw.transcript:
            sw.transcript = caption[:2000]  # at least analyze the caption
    return sw


def supadata_transcript(cfg: Config, url: str) -> str:
    """Preferred: pull a reel/short transcript via Composio's Supadata tool.
    Works for Instagram, TikTok, and YouTube URLs — no cookies, no Whisper."""
    try:
        from .composio_client import ComposioClient
        c = ComposioClient(cfg)
        if not c.is_connected("supadata"):
            return ""
        resp = c.execute("SUPADATA_GET_TRANSCRIPT", {"url": url, "text": True})
        data = ComposioClient.unwrap(resp) or {}
        if isinstance(data, dict):
            for k in ("content", "transcript", "text"):
                v = data.get(k)
                if isinstance(v, str) and v.strip():
                    return v
                if isinstance(v, list):  # list of {text,...} segments
                    joined = " ".join(
                        seg.get("text", "") for seg in v if isinstance(seg, dict)
                    ).strip()
                    if joined:
                        return joined
        return ""
    except Exception:
        return ""


def _download_and_transcribe(cfg: Config, url: str, cookies: list[str]) -> str:
    """Download the reel's audio and transcribe via Groq Whisper (if GROQ_API_KEY set)."""
    groq_key = getattr(cfg, "groq_api_key", "") or ""
    if not groq_key:
        return ""
    try:
        from .watcher import transcribe_with_groq
        with tempfile.TemporaryDirectory() as td:
            audio = str(Path(td) / "a.mp3")
            r = _run([
                "yt-dlp", "-x", "--audio-format", "mp3", "--no-warnings",
                *cookies, "-o", str(Path(td) / "a.%(ext)s"), url,
            ], timeout=240)
            mp3s = list(Path(td).glob("*.mp3"))
            if not mp3s:
                return ""
            return transcribe_with_groq(str(mp3s[0]), groq_key) or ""
    except Exception:
        return ""


def _guess_cta(desc: str) -> str:
    for line in desc.splitlines():
        low = line.lower()
        if any(k in low for k in ("follow", "comment", "subscribe", "link in bio", "dm ", "save this")):
            return line.strip()[:160]
    return ""


# ---------- LLM enrichment ----------

_ENRICH_SYSTEM = "You analyze viral short-form videos. Return ONLY valid JSON."
_ENRICH_PROMPT = """Here is a viral short-form video's data:
- creator: {creator}
- views: {views}
- title/first words: {hook}
- transcript (auto-captions, may be messy):
\"\"\"{transcript}\"\"\"

Extract, as JSON:
{{
  "hook": "the exact scroll-stopping opening line (clean it up from the transcript)",
  "cta": "the call to action if any, else ''",
  "format": "talking_head | skit | screen_record | listicle | story | demo | reaction | other",
  "niche": "the topic/niche in 2-3 words",
  "why_it_worked": "1-2 sentences: the specific reason this hooked and held viewers"
}}
"""


def enrich(cfg: Config, sw: Swipe) -> Swipe:
    llm = LLMClient(cfg)
    if not llm.available() or not sw.transcript:
        return sw
    try:
        out = llm.complete(
            system=_ENRICH_SYSTEM,
            user=_ENRICH_PROMPT.format(
                creator=sw.creator or "?", views=sw.views,
                hook=sw.hook or "?", transcript=sw.transcript[:4000],
            ),
            max_tokens=600,
        )
        j = _extract_json(out)
        sw.hook = j.get("hook") or sw.hook
        sw.cta = j.get("cta") or sw.cta
        sw.format = j.get("format") or sw.format
        sw.niche = j.get("niche") or sw.niche
        sw.why_it_worked = j.get("why_it_worked") or sw.why_it_worked
    except Exception:
        pass
    return sw


# ---------- pattern analysis ----------

_PATTERN_SYSTEM = (
    "You are a viral short-form strategist. You reverse-engineer what makes videos hit "
    "1M+ views and turn it into a concrete, repeatable playbook. Return markdown."
)


def analyze_patterns(cfg: Config, entries: list[dict[str, Any]]) -> str:
    llm = LLMClient(cfg)
    if not llm.available():
        return "No LLM backend available."
    corpus = []
    for e in entries:
        corpus.append(
            f"- [{e.get('views','?')} views] {e.get('creator','?')} | hook: \"{e.get('hook','')}\" "
            f"| format: {e.get('format','')} | cta: {e.get('cta','')} | why: {e.get('why_it_worked','')}"
        )
    prompt = (
        "Below are proven viral short-form videos (real view counts). Reverse-engineer the "
        "patterns for a creator in the AI / automation niche who wants 1M views + 10K followers.\n\n"
        + "\n".join(corpus) +
        "\n\nReturn markdown with: (1) the 5 hook patterns that repeat, with a fill-in-the-blank "
        "template each; (2) common structures/pacing; (3) CTA patterns; (4) 5 specific reel ideas "
        "for the AI-automation niche modeled on these winners; (5) the single biggest lever."
    )
    return llm.complete(system=_PATTERN_SYSTEM, user=prompt, max_tokens=2500)


# ---------- dashboard ----------

def build_dashboard(entries: list[dict[str, Any]], out_path: str | None = None) -> str:
    root = Path(__file__).resolve().parent.parent.parent
    out = Path(out_path) if out_path else root / "content" / "swipe_dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for e in sorted(entries, key=lambda x: x.get("views", 0), reverse=True):
        views = e.get("views", 0)
        vtxt = f"{views/1_000_000:.1f}M" if views >= 1_000_000 else (f"{views/1000:.0f}K" if views >= 1000 else str(views))
        rows.append(f"""
      <tr>
        <td class="v">{vtxt}</td>
        <td>{_esc(e.get('creator',''))}<div class="nm">{_esc(e.get('niche',''))}</div></td>
        <td class="hook">{_esc(e.get('hook',''))}</td>
        <td>{_esc(e.get('format',''))}</td>
        <td>{_esc(e.get('cta',''))}</td>
        <td class="why">{_esc(e.get('why_it_worked',''))}</td>
        <td><a href="{_esc(e.get('url',''))}" target="_blank">open</a></td>
      </tr>""")
    html = _DASH_TEMPLATE.replace("{{ROWS}}", "\n".join(rows)).replace("{{COUNT}}", str(len(entries)))
    out.write_text(html)
    return str(out)


def _esc(s: Any) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


_DASH_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Viral Swipe File</title>
<style>
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#0b0b0f;color:#e8e8ec;margin:0;padding:2rem}
h1{font-size:1.5rem;margin:0 0 .25rem}.sub{color:#8a8a99;margin-bottom:1.5rem}
table{width:100%;border-collapse:collapse;font-size:.86rem}
th,td{text-align:left;padding:.7rem .6rem;border-bottom:1px solid #23232b;vertical-align:top}
th{color:#9a9aa8;font-size:.7rem;text-transform:uppercase;letter-spacing:.08em}
.v{font-weight:800;color:#4ade80;white-space:nowrap}
.hook{font-weight:600;max-width:280px}.why{color:#a9a9b8;max-width:260px}
.nm{color:#6f6f7e;font-size:.72rem}a{color:#818cf8}
tr:hover{background:#141420}
</style></head><body>
<h1>🎯 Viral Swipe File</h1>
<div class="sub">{{COUNT}} proven videos · reverse-engineered · sorted by views</div>
<table>
<thead><tr><th>Views</th><th>Creator</th><th>Hook</th><th>Format</th><th>CTA</th><th>Why it worked</th><th></th></tr></thead>
<tbody>
{{ROWS}}
</tbody></table>
</body></html>"""
