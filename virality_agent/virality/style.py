"""User-style profile + the 8 content pillars.

The pillar config lives in pillars.json (committed; rotate forever).
The style profile lives in style.json (gitignored, written once via
`virality.cli setup-style` — re-run any time to update).

Every script generation reads BOTH so the engine is constrained to
your voice while still drawing from the proven viral patterns.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PILLARS_PATH = _HERE / "pillars.json"
_STYLE_PATH = _HERE / "style.json"


@dataclass
class Pillar:
    id: int
    name: str
    tagline: str
    why_it_works: str
    hook_patterns: list[str]
    structure_beats: list[str]
    spice_swap_focus: list[str] = field(default_factory=list)


@dataclass
class StyleProfile:
    creator_name: str = ""
    niche_specifics: str = ""           # what they actually sell ("$3k AI websites for plumbers")
    target_audience: str = ""           # who they want to reach
    avatar: str = ""                    # Callaway lock: the SINGLE viewer every reel must serve
    voice_tone: str = ""                # "blunt, energetic, no-fluff"
    do_say: list[str] = field(default_factory=list)        # phrases / words they like
    do_not_say: list[str] = field(default_factory=list)    # banned words / cringe lines
    cta_style: str = ""                 # "comment one word", "DM the word PLAYBOOK", etc
    signature_lines: list[str] = field(default_factory=list)  # catchphrases / sign-offs
    grade_level: int = 5                # reading level cap

    @classmethod
    def load(cls) -> "StyleProfile":
        if not _STYLE_PATH.exists():
            return cls()
        try:
            data = json.loads(_STYLE_PATH.read_text())
        except json.JSONDecodeError:
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self) -> Path:
        _STYLE_PATH.write_text(json.dumps(asdict(self), indent=2))
        return _STYLE_PATH

    def is_set(self) -> bool:
        return bool(self.creator_name or self.niche_specifics or self.voice_tone)

    def as_prompt_block(self) -> str:
        lines = ["YOUR STYLE (always honor this — viral patterns must bend to fit YOU):"]
        if self.creator_name:
            lines.append(f"- Creator: {self.creator_name}")
        if self.niche_specifics:
            lines.append(f"- What you sell: {self.niche_specifics}")
        if self.target_audience:
            lines.append(f"- Audience: {self.target_audience}")
        if self.avatar:
            lines.append(
                f"- LOCKED AVATAR (every reel must serve this exact viewer — algorithm "
                f"only boosts when audience stays consistent): {self.avatar}"
            )
        if self.voice_tone:
            lines.append(f"- Voice: {self.voice_tone}")
        if self.do_say:
            lines.append(f"- Say things like: {', '.join(self.do_say)}")
        if self.do_not_say:
            lines.append(f"- NEVER say: {', '.join(self.do_not_say)}")
        if self.cta_style:
            lines.append(f"- CTA style: {self.cta_style}")
        if self.signature_lines:
            lines.append(f"- Signature lines (use sparingly): {' / '.join(self.signature_lines)}")
        lines.append(f"- Reading level: grade {self.grade_level}")
        return "\n".join(lines)


def load_pillars() -> list[Pillar]:
    data = json.loads(_PILLARS_PATH.read_text())
    return [Pillar(**p) for p in data.get("pillars", [])]


def get_pillar(pid: int | str) -> Pillar:
    pillars = load_pillars()
    if isinstance(pid, int) or (isinstance(pid, str) and pid.isdigit()):
        n = int(pid)
        for p in pillars:
            if p.id == n:
                return p
    if isinstance(pid, str):
        s = pid.strip().lower()
        for p in pillars:
            if p.name.lower() == s:
                return p
    raise KeyError(f"unknown pillar: {pid!r}. options: " +
                   ", ".join(f"{p.id}={p.name}" for p in load_pillars()))


def pillar_prompt_block(p: Pillar) -> str:
    lines = [
        f"PILLAR: {p.name} — {p.tagline}",
        f"Why it works: {p.why_it_works}",
        "Proven hook patterns (study, do not copy verbatim):",
    ]
    for h in p.hook_patterns:
        lines.append(f"  - {h}")
    lines.append("Required structural beats:")
    for b in p.structure_beats:
        lines.append(f"  - {b}")
    return "\n".join(lines)
