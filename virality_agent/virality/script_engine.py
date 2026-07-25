"""Generate a fresh viral script in the user's voice from analyzed competitors,
then iterate it: 5th-grade rewrite → spice swaps → score → loop."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .analyzer import Analysis, _extract_json
from .config import Config
from .llm import LLMClient
from .style import Pillar, StyleProfile, pillar_prompt_block
from .video_intel import VideoFacts


DEFAULT_NICHE = (
    "AI websites + ads automation. Sells $1k-$5k AI-built websites and "
    "Meta/Google ads automation services to local businesses and solopreneurs."
)

# Word swaps that punch: neutral verb → spicier framing.
SPICE_SWAPS = [
    ("using", "abusing"),
    ("learning", "stealing"),
    ("trying", "exploiting"),
    ("helping", "rigging"),
    ("growing", "hijacking"),
    ("building", "weaponizing"),
    ("posting", "blasting"),
    ("making money with", "milking"),
    ("automating", "auto-printing money with"),
]


WRITER_SYSTEM = (
    "You are a short-form Instagram scriptwriter for the AI-website + ads niche. "
    "You write 30-45 second reel scripts that hook in 3 seconds and never let go. "
    "You ALWAYS write in the creator's own voice (their style profile is the source of truth) "
    "and you ALWAYS honor the chosen pillar's structural beats. "
    "You always return one valid JSON object. No prose outside JSON."
)

WRITER_PROMPT = """Write a brand-new Instagram reel script (30-45s, ~110 words).

{style_block}

{pillar_block}

INSPIRATION (top-performing competitor reels and their analyses):
{inspiration}

WRITING RULES
- {grade_rule}
- Hook in the first 3 seconds. Use one of the pillar's hook patterns as a STARTING POINT, then bend it to the creator's voice — never copy verbatim.
- Use a punchy "spicy" verb where neutral verbs would normally go (e.g. "abusing" instead of "using"). Pick 1-3 spots — do not overdo it.
- Concrete numbers and specific niches over abstractions.
- One clear CTA that matches the creator's CTA style.

Return JSON:
{{
  "hook": "first 3 seconds, verbatim",
  "script": "full ~110-word script with line breaks for delivery",
  "b_roll": ["3-6 visual cues to film/screen-record per beat"],
  "caption": "the caption to post with 3-6 hashtags at the end",
  "title_options": ["3 punchy titles under 60 chars"],
  "cta": "the spoken CTA line"
}}
"""

CRITIC_SYSTEM = (
    "You are a ruthless short-form script critic. You score against the Callaway model "
    "of how the IG algorithm distributes: avatar consistency, the 4 Horsemen of "
    "engagement, and the 5 comment drivers. You always return one valid JSON object."
)

CRITIC_PROMPT = """Score this script the way IG actually distributes it (Callaway model).

CREATOR'S LOCKED AVATAR (the SINGLE viewer the account must consistently serve;
the algorithm cascade-boosts only when this stays the same across reels):
{avatar_block}

SCRIPT
\"\"\"{script}\"\"\"
HOOK
\"\"\"{hook}\"\"\"
CTA
\"\"\"{cta}\"\"\"

Return JSON with this EXACT shape:
{{
  "audience_match": {{
    "score_0_25": 0,
    "fits_locked_avatar": true,
    "reasoning": "specific — does this serve THE avatar, or does it drift to a different viewer?",
    "topic_drift_warning": "blank if aligned, otherwise the exact mismatch"
  }},
  "four_horsemen": {{
    "relevant_0_25": 0,
    "non_obvious_tactical_0_25": 0,
    "high_absorption_0_25": 0,
    "short_distance_to_implement_0_25": 0,
    "notes": "one line per horseman"
  }},
  "comment_drivers": {{
    "hard_stance_0_5": 0,
    "contrarian_side_0_5": 0,
    "ratchet_framing_0_5": 0,
    "cult_brands_0_5": 0,
    "drive_emotion_0_5": 0,
    "predicted_top_comment": "the single comment most viewers would leave"
  }},
  "score_0_100": 0,
  "reading_grade_level_estimate": 0,
  "hook_strength": "weak | ok | strong",
  "drivers": ["what's working"],
  "leaks": ["what's hurting it — call out audience drift first if present"],
  "rewrite_priorities": ["top 3 specific edits to try next, ranked by impact on the cascade"]
}}

SCORING RULES
- score_0_100 = audience_match.score_0_25 + sum(four_horsemen) — capped at 100. Comment drivers are diagnostic, not summed in.
- If topic_drift_warning is non-blank, audience_match.score_0_25 must be <= 8 and total cannot exceed 60. Drift kills cascades.
- rewrite_priorities[0] must address the lowest sub-score above. No vague advice.
"""


@dataclass
class Script:
    hook: str = ""
    script: str = ""
    b_roll: list[str] = field(default_factory=list)
    caption: str = ""
    title_options: list[str] = field(default_factory=list)
    cta: str = ""
    score: int = 0
    critique: dict[str, Any] = field(default_factory=dict)
    iteration: int = 0

    @classmethod
    def from_json(cls, j: dict[str, Any]) -> "Script":
        return cls(
            hook=str(j.get("hook", "")),
            script=str(j.get("script", "")),
            b_roll=list(j.get("b_roll") or []),
            caption=str(j.get("caption", "")),
            title_options=list(j.get("title_options") or []),
            cta=str(j.get("cta", "")),
        )


class ScriptEngine:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.llm = LLMClient(cfg)

    def _build_prompt(
        self,
        inspiration: str,
        pillar: Pillar | None,
        style: StyleProfile | None,
    ) -> str:
        style = style or StyleProfile.load()
        if not style.is_set():
            style_block = (
                "YOUR STYLE: not configured. Falling back to the default niche profile:\n"
                f"- {DEFAULT_NICHE}\n"
                "- Voice: blunt, energetic, no fluff. Audience: small-business owners.\n"
                "- Run `python -m virality.cli setup-style` to lock in your real voice."
            )
            grade = 5
        else:
            style_block = style.as_prompt_block()
            grade = style.grade_level
        pillar_block = pillar_prompt_block(pillar) if pillar else (
            "PILLAR: free-pick. Use whichever of the 8 pillars (speed builds, "
            "cost killers, money proofs, mistakes, tool stacks, niche use cases, "
            "hot takes, behind-the-scenes) best fits the inspiration."
        )
        return WRITER_PROMPT.format(
            style_block=style_block,
            pillar_block=pillar_block,
            inspiration=inspiration,
            grade_rule=f"Grade-{grade} reading level. Short words, short lines.",
        )

    def generate(
        self,
        analyses: list[tuple[VideoFacts, Analysis]],
        custom_topic: str | None = None,
        pillar: Pillar | None = None,
        style: StyleProfile | None = None,
    ) -> Script:
        if not self.llm.available():
            raise RuntimeError("No LLM backend available (set KIRO_API_KEY or ANTHROPIC_API_KEY).")
        inspiration_blocks = []
        for facts, ana in analyses[:5]:
            inspiration_blocks.append(json.dumps({
                "url": facts.url,
                "topic": ana.topic,
                "hook": ana.hook_text,
                "hook_type": ana.hook_type,
                "score": ana.score,
                "angles": ana.angles,
            }, indent=2))
        prompt = self._build_prompt(
            "\n\n".join(inspiration_blocks) or "(none — write a fresh banger)",
            pillar,
            style,
        )
        if custom_topic:
            prompt += f"\n\nFORCED TOPIC: {custom_topic}"
        text = self.llm.complete(system=WRITER_SYSTEM, user=prompt, max_tokens=1500)
        return Script.from_json(_extract_json(text))

    def apply_spice(self, script: Script, max_swaps: int = 3) -> Script:
        """Replace neutral verbs with spicier ones. Bounded count to keep voice consistent."""
        out_text = script.script
        out_hook = script.hook
        used = 0
        for plain, spicy in SPICE_SWAPS:
            if used >= max_swaps:
                break
            new_text = _smart_replace(out_text, plain, spicy)
            new_hook = _smart_replace(out_hook, plain, spicy)
            if new_text != out_text or new_hook != out_hook:
                out_text = new_text
                out_hook = new_hook
                used += 1
        script.script = out_text
        script.hook = out_hook
        return script

    def critique(self, script: Script, style: StyleProfile | None = None) -> Script:
        if not self.llm.available():
            raise RuntimeError("No LLM backend available (set KIRO_API_KEY or ANTHROPIC_API_KEY).")
        style = style or StyleProfile.load()
        avatar_block = (
            style.avatar
            if style.avatar
            else f"(no locked avatar — falling back to: {style.target_audience or 'small-business owners curious about AI'})"
        )
        text = self.llm.complete(
            system=CRITIC_SYSTEM,
            user=CRITIC_PROMPT.format(
                avatar_block=avatar_block,
                script=script.script,
                hook=script.hook,
                cta=script.cta,
            ),
            max_tokens=1400,
        )
        j = _extract_json(text)
        script.critique = j
        try:
            script.score = int(j.get("score_0_100", 0) or 0)
        except (TypeError, ValueError):
            script.score = 0
        return script

    def iterate(
        self,
        analyses: list[tuple[VideoFacts, Analysis]],
        rounds: int = 3,
        target_score: int = 85,
        custom_topic: str | None = None,
        pillar: Pillar | None = None,
        style: StyleProfile | None = None,
    ) -> list[Script]:
        history: list[Script] = []
        current = self.generate(
            analyses, custom_topic=custom_topic, pillar=pillar, style=style
        )
        current = self.apply_spice(current)
        current = self.critique(current, style=style)
        current.iteration = 0
        history.append(current)
        for i in range(1, rounds + 1):
            if current.score >= target_score:
                break
            current = self._rewrite(current, analyses, custom_topic, pillar, style)
            current = self.apply_spice(current)
            current = self.critique(current, style=style)
            current.iteration = i
            history.append(current)
        return history

    def _rewrite(
        self,
        prev: Script,
        analyses: list[tuple[VideoFacts, Analysis]],
        custom_topic: str | None,
        pillar: Pillar | None = None,
        style: StyleProfile | None = None,
    ) -> Script:
        priorities = prev.critique.get("rewrite_priorities") or []
        rewrite_prompt = (
            "Rewrite this script. Keep what worked, fix what didn't.\n\n"
            f"PREVIOUS SCRIPT:\n\"\"\"{prev.script}\"\"\"\n\n"
            f"PREVIOUS SCORE: {prev.score}\n"
            f"FIX THESE FIRST:\n- " + "\n- ".join(priorities or ["weak hook", "fluffy CTA"])
            + "\n\nReturn the same JSON shape as before."
        )
        prompt = self._build_prompt("(see previous round)", pillar, style) + "\n\n" + rewrite_prompt
        if custom_topic:
            prompt += f"\n\nFORCED TOPIC: {custom_topic}"
        text = self.llm.complete(system=WRITER_SYSTEM, user=prompt, max_tokens=1500)
        return Script.from_json(_extract_json(text))


def _smart_replace(text: str, needle: str, sub: str) -> str:
    """Case-aware single-pass replace on whole-word matches."""
    if not needle or not text:
        return text
    import re
    pattern = re.compile(rf"\b{re.escape(needle)}\b", re.IGNORECASE)
    def _repl(m: re.Match) -> str:
        original = m.group(0)
        if original.isupper():
            return sub.upper()
        if original[0].isupper():
            return sub[0].upper() + sub[1:]
        return sub
    return pattern.sub(_repl, text, count=1)
