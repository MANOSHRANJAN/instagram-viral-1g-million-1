"""Claude-powered analysis: hook diagnosis + Callaway-framework virality score.

Multimodal: when frames are available (from ReelWatcher), they go in as
vision content blocks so the analyzer sees what's on screen — text overlays,
opening shots, on-screen numbers, faces, products.

Scoring is built around the Callaway model of how IG actually distributes:
- The algorithm matchmakes by topic + avatar consistency across your previous reels.
- It tests on a 200-person sample (mostly non-followers), then cascades 200 → 2K → 20K → 200K.
- The 4 Horsemen of engagement: Relevant, Non-Obvious & Tactical, High Absorption,
  Short Distance to Implementation.
- The 5 comment drivers: Hard Stance, Contrarian Side, Ratchet Framing,
  Cult-Loved Brands, Drive Emotion.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .config import Config
from .llm import LLMClient
from .style import StyleProfile
from .video_intel import VideoFacts
from .watcher import frame_to_b64


ANALYZER_SYSTEM = """You are a short-form virality analyst for Instagram reels.
You break down WHY a reel works, with brutal honesty and specificity.
You score against the Callaway model of how the IG algorithm actually distributes:
matchmaking by avatar consistency, then a 200-person sample group, then a cascade boost.
You watch the frames AND read the transcript — visual hooks (text overlays,
opening shots, on-screen numbers, faces) matter as much as spoken words.
Your output is always a single valid JSON object. No prose outside the JSON.
"""

ANALYZER_PROMPT = """Analyze this Instagram reel for an AI-niche creator.

CREATOR'S LOCKED AVATAR (the SINGLE viewer their account must consistently serve;
the algorithm only boosts reels that match this avatar over and over):
{avatar_block}

REEL METADATA
- url: {url}
- author: {author}
- views: {views} | likes: {likes} | comments: {comments}
- duration_seconds: {duration}
- caption: {caption}

TRANSCRIPT (truncated)
\"\"\"{transcript}\"\"\"

The first images below are the 0-10s HOOK MICROSCOPE (dense 2fps sample of the opening).
The remaining images are SCENE-CHANGE FRAMES across the rest of the reel.

Return JSON with this EXACT shape (no extra fields, no missing fields):
{{
  "hook": {{
    "first_3_seconds": "verbatim spoken words in the opening",
    "visual_hook": "what is on screen in seconds 0-3 (text overlay, opening shot, framing, on-screen number, face)",
    "hook_type": "one of: shock | curiosity_gap | bold_claim | pattern_interrupt | question | listicle | demo | story | call_out",
    "why_it_grabs": "1-2 sentences combining the visual + audible reasons it stops the scroll"
  }},
  "structure": {{
    "beats": ["beat 1", "beat 2", "..."],
    "retention_tricks": ["specific moves used to keep watching — visual cuts, on-screen text reveals, pacing"],
    "cta": "what they ask the viewer to do (visual + spoken)"
  }},
  "visual_style": {{
    "format": "talking head | screen-record | demo | text-on-screen | meme | montage | timelapse | mixed",
    "text_overlay_usage": "none | sparse | constant",
    "cuts_per_10s_estimate": 0,
    "dominant_color_or_aesthetic": "short description"
  }},
  "audience_match": {{
    "score_0_25": 0,
    "fits_locked_avatar": true,
    "reasoning": "why this reel does or does not serve the creator's locked avatar — be specific about who it actually attracts vs who it should",
    "topic_drift_warning": "blank if aligned, otherwise the exact mismatch (this kills cascade boost)"
  }},
  "four_horsemen": {{
    "relevant_0_25": 0,
    "non_obvious_tactical_0_25": 0,
    "high_absorption_0_25": 0,
    "short_distance_to_implement_0_25": 0,
    "notes": "one line per horseman explaining the score"
  }},
  "comment_drivers": {{
    "hard_stance_0_5": 0,
    "contrarian_side_0_5": 0,
    "ratchet_framing_0_5": 0,
    "cult_brands_0_5": 0,
    "drive_emotion_0_5": 0,
    "predicted_top_comment": "the single comment most viewers would leave"
  }},
  "virality_score": {{
    "score_0_100": 0,
    "drivers": ["top 3 things working — include at least one visual driver"],
    "leaks": ["top 3 things hurting reach — call out audience drift first if present"]
  }},
  "topic": "the underlying AI topic in one phrase",
  "transferable_angles": ["3-5 angle prompts you could remix for THIS creator's locked avatar"]
}}

SCORING RULES
- score_0_100 = audience_match.score_0_25 + sum(four_horsemen) — capped at 100. Comment drivers are diagnostic, not summed in.
- If topic_drift_warning is non-blank, audience_match.score_0_25 must be <= 8 and the reel cannot exceed 60 overall — drift is the #1 reach killer in the Callaway model.
"""


@dataclass
class Analysis:
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def hook_text(self) -> str:
        return (self.raw.get("hook") or {}).get("first_3_seconds", "")

    @property
    def visual_hook(self) -> str:
        return (self.raw.get("hook") or {}).get("visual_hook", "")

    @property
    def hook_type(self) -> str:
        return (self.raw.get("hook") or {}).get("hook_type", "")

    @property
    def topic(self) -> str:
        return self.raw.get("topic", "")

    @property
    def score(self) -> int:
        return int((self.raw.get("virality_score") or {}).get("score_0_100", 0) or 0)

    @property
    def angles(self) -> list[str]:
        return list(self.raw.get("transferable_angles") or [])

    @property
    def visual_style(self) -> dict[str, Any]:
        return self.raw.get("visual_style") or {}

    @property
    def audience_match(self) -> dict[str, Any]:
        return self.raw.get("audience_match") or {}

    @property
    def four_horsemen(self) -> dict[str, Any]:
        return self.raw.get("four_horsemen") or {}

    @property
    def comment_drivers(self) -> dict[str, Any]:
        return self.raw.get("comment_drivers") or {}

    @property
    def topic_drift(self) -> str:
        return str(self.audience_match.get("topic_drift_warning") or "").strip()


class HookAnalyzer:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.llm = LLMClient(cfg)

    def analyze(self, facts: VideoFacts) -> Analysis:
        if not self.llm.available():
            raise RuntimeError(
                "No LLM backend available. Set KIRO_API_KEY (kiro-cli) or "
                "ANTHROPIC_API_KEY in kiro.env / anthropic.env."
            )
        style = StyleProfile.load()
        avatar_block = (
            style.avatar
            if style.avatar
            else f"(no locked avatar — falling back to: {style.target_audience or 'small-business owners curious about AI'})"
        )
        prompt_text = ANALYZER_PROMPT.format(
            avatar_block=avatar_block,
            url=facts.url,
            author=facts.author or "(unknown)",
            views=facts.views if facts.views is not None else "?",
            likes=facts.likes if facts.likes is not None else "?",
            comments=facts.comments if facts.comments is not None else "?",
            duration=facts.duration_seconds if facts.duration_seconds is not None else "?",
            caption=(facts.caption or "")[:500],
            transcript=(facts.transcript or facts.caption or "(no transcript available)")[:6000],
        )

        # Collect hook/scene frames as base64 (used only by the vision-capable
        # anthropic backend; the kiro-cli backend is text-only and ignores them).
        images_b64: list[str] = []
        if facts.has_visuals() and facts.watch:
            for frame_path in facts.watch.all_frames(max_total=12):
                try:
                    images_b64.append(frame_to_b64(frame_path))
                except Exception:
                    continue

        text = self.llm.complete(
            system=ANALYZER_SYSTEM,
            user=prompt_text,
            max_tokens=3200,
            images_b64=images_b64,
        )
        return Analysis(raw=_extract_json(text))


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return {"_raw": text}
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {"_raw": text}
