# virality_agent

An Instagram-only virality engine for the AI-content niche.

It does four things, end-to-end:

1. **Discover** AI-niche creators on Instagram (Exa-powered, with a curated seed list as fallback).
2. **Scroll** a competitor's profile and rank their reels by engagement.
3. **Analyze** a reel — pull caption + transcript, diagnose the hook, score it 0-100.
4. **Mine + iterate** scripts: pull the best reels across N competitors, write a fresh script in your voice (5th-grade reading level, with sharp word swaps like `using → abusing`), then critique → rewrite → loop.

Powered by Composio (Firecrawl for IG scraping, Exa for discovery) and Claude Opus 4.7+.

## Setup

```bash
pip install -r requirements.txt
```

Composio key is auto-loaded from `../composio.env`. Anthropic key is auto-loaded from `../anthropic.env`. No further env setup needed.

**One-time:** add a Firecrawl auth config in [dashboard.composio.dev](https://dashboard.composio.dev) → Auth Configs → Firecrawl → paste your Firecrawl API key. (Composio doesn't ship managed Firecrawl auth on the free tier.) Optionally do the same for Exa to get live competitor discovery.

Verify:

```bash
python -m virality.cli status
```

## Commands

```bash
# What's connected
python -m virality.cli status

# Find AI-niche IG creators (Exa if connected, falls back to seed list)
python -m virality.cli discover --niche "ai automation small business" -n 10

# Scroll one profile and list their top reels
python -m virality.cli scroll @heyriley --top 5

# Audit one creator: scroll → analyze → score each top reel
python -m virality.cli audit @heyriley --top 5

# Analyze a single reel
python -m virality.cli analyze "https://www.instagram.com/reel/Cxyz/"

# Mine multiple competitors and write a fresh script
python -m virality.cli mine @heyriley @aiwarper @aitechtips \
  --per-creator 3 --max-videos 8 -r 2 --target 85 \
  --topic "n8n automations for restaurants"

# Manual: feed your own list of reel URLs and iterate
python -m virality.cli iterate \
  -u "https://www.instagram.com/reel/<a>/" \
  -u "https://www.instagram.com/reel/<b>/" \
  -r 3 --target 85
```

## Architecture

```
virality/
  config.py         loads keys from composio.env + anthropic.env
  composio_client.py SDK wrapper, version-pinned execute, auth helper
  competitors.py    Exa-powered discovery + IG-only seed list
  ig_scroller.py    Profile feed → top reels by engagement
  video_intel.py    Firecrawl extract for a reel (caption + transcript + counts)
  analyzer.py       Claude: hook type, retention tricks, virality score, angles
  script_engine.py  Claude writer + critic loop + spice-swap iterator
  cli.py            argparse front-end
```

## Spice swaps

A bounded list of neutral → punchy verb swaps applied 1–3 times per script:

| neutral       | spicy                       |
|---------------|-----------------------------|
| using         | abusing                     |
| learning      | stealing                    |
| trying        | exploiting                  |
| building      | weaponizing                 |
| automating    | auto-printing money with    |

Whole-word, case-aware (`Using` → `Abusing`). Applied after generation so the writer focuses on structure, not vocabulary. Edit `SPICE_SWAPS` in `script_engine.py` to tune.
