"""Loads keys from the user's composio.env / anthropic.env and the package's .env."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


def _load_env() -> dict[str, str]:
    here = Path(__file__).resolve().parent.parent
    workspace = here.parent
    merged: dict[str, str] = {}
    for candidate in (workspace / "composio.env", workspace / "elevenlabs.env", here / ".env"):
        if candidate.exists():
            for k, v in dotenv_values(candidate).items():
                if v is None:
                    continue
                merged[k] = v.strip().strip('"').strip("'")
    anth = workspace / "anthropic.env"
    if anth.exists():
        merged.update(_parse_anthropic_env(anth.read_text()))
    # kiro.env overrides anthropic.env — add your Kiro API key there
    kiro = workspace / "kiro.env"
    if kiro.exists():
        for k, v in dotenv_values(kiro).items():
            if v is None:
                continue
            v = v.strip().strip('"').strip("'")
            if v and not v.startswith("your_"):  # skip unfilled placeholders
                merged[k] = v
    for k, v in os.environ.items():
        if v:
            merged[k] = v
    return merged


def _find_kiro_cli(explicit: str = "") -> str:
    """Return a usable kiro-cli path, or '' if not found."""
    import shutil
    if explicit and Path(explicit).exists():
        return explicit
    found = shutil.which("kiro-cli")
    if found:
        return found
    fallback = Path.home() / ".local" / "bin" / "kiro-cli"
    return str(fallback) if fallback.exists() else ""


def _parse_anthropic_env(text: str) -> dict[str, str]:
    """anthropic.env may be a curl command or KEY=VALUE pairs. Handle both."""
    out: dict[str, str] = {}
    # KEY=VALUE form first
    for line in text.splitlines():
        m = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.+?)\s*$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    # curl form: extract x-api-key, base URL, model
    if "curl" in text:
        m = re.search(r"x-api-key:\s*([^\s'\"]+)", text)
        if m:
            out.setdefault("ANTHROPIC_API_KEY", m.group(1))
        m = re.search(r"https?://[^\s'\"/]+(?:/[^\s'\"]*)?", text)
        if m:
            url = m.group(0).rstrip("/")
            # strip trailing /v1/messages-style path; keep host root
            url = re.sub(r"/v1/messages.*$", "", url)
            out.setdefault("ANTHROPIC_BASE_URL", url)
        m = re.search(r'"model"\s*:\s*"([^"]+)"', text)
        if m:
            out.setdefault("CLAUDE_MODEL", m.group(1))
    return out


@dataclass
class Config:
    composio_api_key: str
    anthropic_api_key: str
    anthropic_base_url: str = ""
    user_id: str = "virality_agent"
    exa_version: str = "20260615_00"
    firecrawl_version: str = "latest"
    claude_model: str = "claude-opus-4-7"
    ig_chrome_profile: str = "Default"
    ig_cookies_file: str = ""
    watch_reels: bool = True
    # LLM backend: "auto" | "kiro_cli" | "anthropic".
    # "kiro_cli" drives Claude via your Kiro subscription (kiro-cli headless).
    llm_backend: str = "auto"
    kiro_api_key: str = ""
    kiro_cli_path: str = ""
    kiro_model: str = "auto"
    # ElevenLabs text-to-speech
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_model: str = "eleven_multilingual_v2"
    # Groq (optional) — transcribes Instagram/TikTok reel audio for the swipe file
    groq_api_key: str = ""

    @classmethod
    def load(cls) -> "Config":
        env = _load_env()
        composio_key = env.get("COMPOSIO_API_KEY") or env.get("apikey") or env.get("APIKEY", "")
        anthropic_key = env.get("ANTHROPIC_API_KEY", "")
        if not composio_key:
            raise RuntimeError(
                "COMPOSIO_API_KEY not found. Put it in composio.env (apikey=...) "
                "or virality_agent/.env."
            )
        # Auto-detect a cookies file at the workspace root if env var isn't set
        cookies_file = env.get("IG_COOKIES_FILE", "")
        if not cookies_file:
            workspace = Path(__file__).resolve().parent.parent.parent
            for name in ("instagram_cookies.txt", "ig_cookies.txt", "cookies.txt"):
                p = workspace / name
                if p.exists():
                    cookies_file = str(p)
                    break
        return cls(
            composio_api_key=composio_key,
            anthropic_api_key=anthropic_key,
            anthropic_base_url=env.get("ANTHROPIC_BASE_URL", ""),
            user_id=env.get("COMPOSIO_USER_ID", "virality_agent"),
            exa_version=env.get("EXA_VERSION", "20260615_00"),
            firecrawl_version=env.get("FIRECRAWL_VERSION", "latest"),
            claude_model=env.get("CLAUDE_MODEL", "claude-opus-4-7"),
            ig_chrome_profile=env.get("IG_CHROME_PROFILE", "Default"),
            ig_cookies_file=cookies_file,
            watch_reels=env.get("WATCH_REELS", "true").lower() != "false",
            llm_backend=env.get("LLM_BACKEND", "auto").strip().lower(),
            kiro_api_key=env.get("KIRO_API_KEY", ""),
            kiro_cli_path=env.get("KIRO_CLI_PATH", ""),
            kiro_model=env.get("KIRO_MODEL", "auto"),
            elevenlabs_api_key=env.get("ELEVENLABS_API_KEY", ""),
            elevenlabs_voice_id=env.get("ELEVENLABS_VOICE_ID", ""),
            elevenlabs_model=env.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
            groq_api_key=env.get("GROQ_API_KEY", ""),
        )

    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    def has_elevenlabs(self) -> bool:
        k = self.elevenlabs_api_key
        return bool(k) and not k.startswith("your_")

    def resolve_backend(self) -> str:
        """Decide which LLM backend to actually use."""
        if self.llm_backend in ("kiro_cli", "kiro", "cli"):
            return "kiro_cli"
        if self.llm_backend == "anthropic":
            return "anthropic"
        # auto: prefer kiro-cli when a Kiro key + binary are available
        if self.kiro_api_key and _find_kiro_cli(self.kiro_cli_path):
            return "kiro_cli"
        if self.anthropic_api_key:
            return "anthropic"
        # last resort: kiro if a key exists even without confirmed binary path
        return "kiro_cli" if self.kiro_api_key else "anthropic"

    def has_llm(self) -> bool:
        backend = self.resolve_backend()
        if backend == "kiro_cli":
            return bool(self.kiro_api_key and _find_kiro_cli(self.kiro_cli_path))
        return bool(self.anthropic_api_key)

    def anthropic_kwargs(self) -> dict[str, str]:
        kw: dict[str, str] = {"api_key": self.anthropic_api_key}
        if self.anthropic_base_url:
            kw["base_url"] = self.anthropic_base_url
        return kw
