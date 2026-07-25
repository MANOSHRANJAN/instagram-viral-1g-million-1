# Instagram Viral — 0 → 1M Growth System

A working toolkit + content system for growing an AI/automation Instagram brand from zero, built around real reverse-engineered data (not guesswork).

## What's inside

| Folder | What it is |
|---|---|
| `dashboard/` | The command center — open `dashboard/index.html` in a browser. Goal tracker, Week 1 content plan with per-day production playbooks, daily ops checklist, analytics log, and research links. |
| `content/` | Strategy + scripts: 90-day growth plan, Week 1 content plan, hook bank, trending topics/newsjacks, account positioning, and generated reels. |
| `research/` | Dated per-scrape research folders (`YYYY-MM-DD_topic/`) — raw scraped posts, transcripts, and a styled HTML report per run. |
| `ig-research/` | The reusable Instagram research tool (CDP scraper, whisper transcription, HTML report generator). See `ig-research/README.md`. |
| `virality_agent/` | Python CLI: generate → spice → critique → score viral scripts, ElevenLabs TTS narration, trend brain. Uses the Kiro LLM backend. |
| `virality_agent_ts/` | Earlier TypeScript experiments + creator framework research (Hormozi, MrBeast, Mosseri, etc.). |

## Setup

1. Copy `env.example` into real env files (`kiro.env`, `elevenlabs.env`, `composio.env`) and fill in your own keys. **These are gitignored — never commit real keys.**
2. Python tool: create a venv and `pip install -r virality_agent/requirements.txt`.
3. Node tool: `cd ig-research && npm install`.

## Notes

- Secrets, `node_modules`, virtualenvs, ML models (`*.bin`), and heavy media (screenshots, audio) are excluded from git via `.gitignore`.
- The dashboard is a static, no-build HTML file — just open it. State (checkboxes, logged numbers) persists in your browser's localStorage.
