"""Push analyzed reels into a NotebookLM notebook via the `nlm` CLI.

You already authed `nlm` (notebooklm-mcp-cli) — we just shell out. Each reel
becomes one source: a structured text dump containing the URL, the hook,
the four-horsemen scores, and the comment-driver scores. NotebookLM can
then answer "what's the avatar these top reels share?" / "what hook
patterns repeat?" with full corpus context.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass


def nlm_available() -> bool:
    return shutil.which("nlm") is not None


@dataclass
class NotebookPushResult:
    notebook_id: str = ""
    sources_added: int = 0
    error: str = ""


def _run(cmd: list[str], stdin_text: str | None = None, timeout: int = 60) -> tuple[int, str, str]:
    p = subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def ensure_notebook(title: str) -> tuple[str, str]:
    """Find a notebook by title, create if missing. Returns (id, error)."""
    rc, out, err = _run(["nlm", "list"], timeout=30)
    if rc != 0:
        return "", f"`nlm list` failed: {err or out}"
    for line in out.splitlines():
        if title in line:
            parts = line.split()
            if parts:
                return parts[0], ""
    rc, out, err = _run(["nlm", "create", title], timeout=30)
    if rc != 0:
        return "", f"`nlm create` failed: {err or out}"
    for token in out.split():
        if len(token) >= 16 and "-" in token:
            return token, ""
    return out.strip(), ""


def _format_source(facts_url: str, ana_raw: dict) -> str:
    hook = ana_raw.get("hook") or {}
    audience = ana_raw.get("audience_match") or {}
    horsemen = ana_raw.get("four_horsemen") or {}
    drivers = ana_raw.get("comment_drivers") or {}
    score = (ana_raw.get("virality_score") or {}).get("score_0_100", 0)
    parts = [
        f"# Reel: {facts_url}",
        f"Topic: {ana_raw.get('topic', '')}",
        f"Score: {score}",
        "",
        "## Hook",
        f"Spoken: {hook.get('first_3_seconds', '')}",
        f"Visual: {hook.get('visual_hook', '')}",
        f"Type: {hook.get('hook_type', '')}",
        f"Why it grabs: {hook.get('why_it_grabs', '')}",
        "",
        "## Audience match (Callaway)",
        f"Score /25: {audience.get('score_0_25', 0)}",
        f"Fits avatar: {audience.get('fits_locked_avatar', '?')}",
        f"Drift: {audience.get('topic_drift_warning') or '(none)'}",
        f"Reasoning: {audience.get('reasoning', '')}",
        "",
        "## Four horsemen",
        f"Relevant /25: {horsemen.get('relevant_0_25', 0)}",
        f"Non-obvious tactical /25: {horsemen.get('non_obvious_tactical_0_25', 0)}",
        f"High absorption /25: {horsemen.get('high_absorption_0_25', 0)}",
        f"Short distance to implement /25: {horsemen.get('short_distance_to_implement_0_25', 0)}",
        f"Notes: {horsemen.get('notes', '')}",
        "",
        "## Comment drivers",
        f"Hard stance /5: {drivers.get('hard_stance_0_5', 0)}",
        f"Contrarian /5: {drivers.get('contrarian_side_0_5', 0)}",
        f"Ratchet framing /5: {drivers.get('ratchet_framing_0_5', 0)}",
        f"Cult brands /5: {drivers.get('cult_brands_0_5', 0)}",
        f"Drive emotion /5: {drivers.get('drive_emotion_0_5', 0)}",
        f"Predicted top comment: {drivers.get('predicted_top_comment', '')}",
        "",
        "## Transferable angles",
    ]
    for a in ana_raw.get("transferable_angles") or []:
        parts.append(f"- {a}")
    parts.append("")
    parts.append("## Raw analysis")
    parts.append(json.dumps(ana_raw, indent=2))
    return "\n".join(parts)


def push_to_notebook(title: str, pairs: list) -> NotebookPushResult:
    """pairs: list of (VideoFacts, Analysis). Adds one source per reel."""
    if not nlm_available():
        return NotebookPushResult(error="`nlm` CLI not on PATH. Skipping NotebookLM push.")
    notebook_id, err = ensure_notebook(title)
    if err or not notebook_id:
        return NotebookPushResult(error=err or "could not resolve notebook id")
    added = 0
    for facts, ana in pairs:
        body = _format_source(facts.url, ana.raw)
        # nlm add <notebook_id> --text -  (stdin)
        rc, _out, e = _run(
            ["nlm", "add", notebook_id, "--text", "-"],
            stdin_text=body,
            timeout=60,
        )
        if rc == 0:
            added += 1
        else:
            # Try alternate flag name some CLI builds use
            rc2, _o2, e2 = _run(
                ["nlm", "source", "add", notebook_id, "--text", "-"],
                stdin_text=body,
                timeout=60,
            )
            if rc2 == 0:
                added += 1
            else:
                return NotebookPushResult(
                    notebook_id=notebook_id,
                    sources_added=added,
                    error=f"`nlm add` failed: {e or e2}",
                )
    return NotebookPushResult(notebook_id=notebook_id, sources_added=added)
