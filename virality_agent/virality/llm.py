"""Unified LLM client for the virality agent.

Two backends, one interface (`LLMClient.complete`):

- "kiro_cli":  drives Claude through your Kiro subscription via the
               `kiro-cli` headless mode (KIRO_API_KEY). No Anthropic key,
               no gateway, no session expiry. Text-only (no vision).
- "anthropic": the classic Anthropic Messages API (supports vision frames).

Backend is chosen by Config.resolve_backend().
"""
from __future__ import annotations

import os
import re
import subprocess
from typing import Any

from .config import Config, _find_kiro_cli


# Strip ANSI colour / cursor escapes and carriage returns the CLI emits.
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07|\r")


def _clean_kiro_output(raw: str) -> str:
    """Remove kiro-cli chrome (banners, warnings, footer) → model text only."""
    text = _ANSI_RE.sub("", raw or "")
    kept: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        # spinner / prompt glyphs the CLI prints
        s = s.lstrip("λ↯▸ ").rstrip()
        if not s:
            continue
        if s.startswith("WARNING:") or low.startswith("warning:"):
            continue
        if "tools are now trusted" in low or "trust-all" in low:
            continue
        if low.startswith("learn more at") or low.startswith("agents can sometimes"):
            continue
        # footer, e.g. "Credits: 0.03 • Time: 15s"
        if "credits:" in low and ("time:" in low or "•" in s):
            continue
        if s.startswith("> "):
            s = s[2:].strip()
        elif s == ">":
            continue
        kept.append(s)
    return "\n".join(kept).strip()


class LLMClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.backend = cfg.resolve_backend()
        self._anthropic = None
        if self.backend == "anthropic" and cfg.has_anthropic():
            from anthropic import Anthropic

            self._anthropic = Anthropic(**cfg.anthropic_kwargs())

    def available(self) -> bool:
        return self.cfg.has_llm()

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1500,
        images_b64: list[str] | None = None,
    ) -> str:
        """Return the model's text. `images_b64` is honoured only by the
        anthropic backend; the kiro_cli backend is text-only."""
        if self.backend == "kiro_cli":
            return self._complete_kiro(system=system, user=user)
        return self._complete_anthropic(
            system=system, user=user, max_tokens=max_tokens, images_b64=images_b64
        )

    # ---- kiro-cli headless backend --------------------------------------
    def _complete_kiro(self, *, system: str, user: str, timeout: int = 240) -> str:
        path = _find_kiro_cli(self.cfg.kiro_cli_path)
        if not path:
            raise RuntimeError(
                "kiro-cli not found. Install it with: "
                "curl -fsSL https://cli.kiro.dev/install | bash"
            )
        if not self.cfg.kiro_api_key:
            raise RuntimeError("KIRO_API_KEY missing — add it to kiro.env.")
        prompt = f"{system.strip()}\n\n{user.strip()}" if system else user.strip()
        cmd = [
            path,
            "chat",
            "--no-interactive",
            "--trust-tools=",  # trust NO tools: pure text generation
            "--model",
            self.cfg.kiro_model or "auto",
            prompt,
        ]
        env = os.environ.copy()
        env["KIRO_API_KEY"] = self.cfg.kiro_api_key
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, env=env, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"kiro-cli timed out after {timeout}s")
        out = _clean_kiro_output(proc.stdout)
        if not out:
            err = _clean_kiro_output(proc.stderr) or (proc.stderr or "").strip()
            raise RuntimeError(
                f"kiro-cli returned no text (exit {proc.returncode}). {err[:300]}"
            )
        return out

    # ---- Anthropic Messages API backend ---------------------------------
    def _complete_anthropic(
        self, *, system: str, user: str, max_tokens: int, images_b64: list[str] | None
    ) -> str:
        if not self._anthropic:
            raise RuntimeError("Anthropic backend not configured (no API key).")
        content: list[dict[str, Any]] = [{"type": "text", "text": user}]
        for b64 in images_b64 or []:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": b64,
                    },
                }
            )
        msg = self._anthropic.messages.create(
            model=self.cfg.claude_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
