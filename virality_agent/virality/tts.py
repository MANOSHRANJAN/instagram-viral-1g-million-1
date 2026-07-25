"""ElevenLabs text-to-speech + voice cloning for the virality agent.

- narrate(): turn a script into an MP3 in your chosen (or cloned) voice.
- clone_voice(): create an Instant Voice Clone from your audio sample(s).
- list_voices(): show the voices available on your account.

Reads ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID from elevenlabs.env (or env).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import Config

# A solid, natural default voice ("Adam") if you haven't cloned/picked one yet.
DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"


@dataclass
class Voice:
    voice_id: str
    name: str
    category: str = ""


def _client(cfg: Config):
    if not cfg.has_elevenlabs():
        raise RuntimeError(
            "ELEVENLABS_API_KEY missing. Add it to elevenlabs.env at the workspace root."
        )
    from elevenlabs.client import ElevenLabs

    return ElevenLabs(api_key=cfg.elevenlabs_api_key)


def list_voices(cfg: Config) -> list[Voice]:
    client = _client(cfg)
    resp = client.voices.get_all()
    out: list[Voice] = []
    for v in getattr(resp, "voices", []) or []:
        out.append(Voice(
            voice_id=getattr(v, "voice_id", ""),
            name=getattr(v, "name", ""),
            category=getattr(v, "category", "") or "",
        ))
    return out


def clone_voice(cfg: Config, name: str, sample_paths: list[str], description: str = "") -> str:
    """Create an Instant Voice Clone. Returns the new voice_id.
    Requires a paid ElevenLabs plan. sample_paths = clean recordings of you talking.
    """
    client = _client(cfg)
    files = []
    for p in sample_paths:
        path = Path(p)
        if not path.exists():
            raise FileNotFoundError(f"sample not found: {p}")
        files.append(path.open("rb"))
    try:
        voice = client.voices.ivc.create(
            name=name,
            description=description or f"Cloned voice for {name}",
            files=files,
        )
    finally:
        for f in files:
            try:
                f.close()
            except Exception:
                pass
    vid = getattr(voice, "voice_id", "") or getattr(voice, "voiceId", "")
    return str(vid)


# Strip markdown/stage-direction noise so only spoken words are narrated.
_MD_RE = re.compile(r"[#*_`>]|\[[^\]]*\]|\([^)]*\)")


def script_to_speech_text(script_text: str) -> str:
    lines = []
    for raw in script_text.splitlines():
        s = _MD_RE.sub("", raw).strip()
        if not s:
            continue
        low = s.lower()
        # skip hashtag-only / label lines
        if low.startswith(("hook", "cta", "script", "caption", "title", "b-roll", "###")):
            # keep the value after a colon if present
            if ":" in s:
                s = s.split(":", 1)[1].strip()
            if not s:
                continue
        if s.startswith("#"):
            continue
        lines.append(s)
    return "\n".join(lines).strip()


_HUMANIZE_SYSTEM = (
    "You are a voiceover director prepping a short-form Instagram reel script for "
    "ElevenLabs text-to-speech. You turn a plain script into a natural, human-sounding "
    "performance script. You output ONLY the performance text — no explanations."
)

_HUMANIZE_PROMPT = """Rewrite the script below as an ElevenLabs performance script so it
sounds like a real, energetic human talking — not a robot reading.

RULES
- Keep the words and meaning. Do NOT add new sentences or change the message.
- Insert natural pauses with break tags: <break time="0.3s" /> for beats,
  <break time="0.6s" /> between ideas. Use them where a human would breathe.
- Add light, tasteful audio tags where they fit the energy (use sparingly, 2-4 total):
  [excited], [sarcastic], [whispers], [laughs], [sigh]. Do not overuse.
- Fix pronunciation by spelling things out phonetically:
  - "n8n" -> "N-eight-N"
  - "$18/day" -> "eighteen bucks a day"
  - "$4k" -> "four grand", "500K" -> "five hundred K"
  - "HVAC" -> "H-VAC", "CTA" -> "C-T-A", "DM" -> "D-M", "AI" stays "AI"
  - "Vapi" -> "Vappy"
  - spell out other acronyms/numbers the way a person would say them
- Use "..." for a dramatic trailing pause where it adds punch.
- Keep the punchy short-line rhythm.

Return ONLY the performance script text (with tags inline). No preamble, no quotes, no markdown.

SCRIPT:
\"\"\"{script}\"\"\"
"""


def humanize_for_tts(cfg: Config, script_text: str) -> str:
    """Use the working LLM (Kiro/Claude) to convert a plain script into an
    ElevenLabs performance script with pauses, breaths, emphasis, and fixed
    pronunciation. Falls back to the raw text if the LLM isn't available."""
    try:
        from .llm import LLMClient
        llm = LLMClient(cfg)
        if not llm.available():
            return script_text
        out = llm.complete(
            system=_HUMANIZE_SYSTEM,
            user=_HUMANIZE_PROMPT.format(script=script_text),
            max_tokens=1200,
        )
        out = out.strip()
        # drop any accidental code fences / leading label
        if out.startswith("```"):
            out = out.strip("`").strip()
        return out or script_text
    except Exception:
        return script_text


def narrate(
    cfg: Config,
    text: str,
    out_path: str,
    voice_id: str = "",
    stability: float = 0.4,
    similarity_boost: float = 0.8,
    style: float = 0.4,
    speed: float = 1.0,
    model_id: str = "",
) -> str:
    """Generate an MP3 from `text`. Returns the output path.
    Tries the expressive model first, falls back to multilingual_v2 if the
    account can't use it."""
    client = _client(cfg)
    vid = voice_id or cfg.elevenlabs_voice_id or DEFAULT_VOICE_ID
    from elevenlabs import VoiceSettings

    settings = VoiceSettings(
        stability=stability,
        similarity_boost=similarity_boost,
        style=style,
        use_speaker_boost=True,
        speed=speed,
    )
    # Prefer the most human model; fall back gracefully.
    candidates = [m for m in (model_id, cfg.elevenlabs_model, "eleven_v3",
                              "eleven_multilingual_v2") if m]
    seen: set[str] = set()
    last_err: Exception | None = None
    for model in candidates:
        if model in seen:
            continue
        seen.add(model)
        try:
            audio = client.text_to_speech.convert(
                voice_id=vid,
                model_id=model,
                text=text,
                output_format="mp3_44100_128",
                voice_settings=settings,
            )
            out = Path(out_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("wb") as f:
                for chunk in audio:
                    if chunk:
                        f.write(chunk)
            return str(out)
        except Exception as exc:  # try the next model
            last_err = exc
            continue
    raise RuntimeError(f"All TTS models failed. Last error: {last_err}")
