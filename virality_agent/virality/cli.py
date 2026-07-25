"""virality — a CLI for the AI-niche virality agent.

Commands:
  status                       show what's connected
  auth <toolkit>               print the redirect URL to connect a toolkit
  analyze <video_url>          deep-dive a single video (transcript + hook + score)
  scroll <ig-handle-or-url>    pull a competitor's top reels
  discover [niche]             find competitor accounts in your niche
  generate -u URL [-u URL...]  pull videos, analyze, write a fresh script
  iterate -u URL ... [-r 3]    generate then loop until score >= target
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .analyzer import HookAnalyzer
from .competitors import CompetitorScout
from .composio_client import ComposioClient
from .config import Config
from .ig_scroller import IGScroller
from .notebook import nlm_available, push_to_notebook
from .script_engine import Script, ScriptEngine
from .style import StyleProfile, get_pillar, load_pillars
from .video_intel import VideoFacts, VideoIntel


console = Console()


def _client(cfg: Config) -> ComposioClient:
    return ComposioClient(cfg)


def cmd_status(cfg: Config, _args: argparse.Namespace) -> int:
    c = _client(cfg)
    accounts = c.list_connected()
    table = Table(title="Composio connections")
    table.add_column("toolkit")
    table.add_column("status")
    table.add_column("user_id")
    table.add_column("id")
    if not accounts:
        table.add_row("(none)", "-", "-", "-")
    for a in accounts:
        tk = a.get("toolkit")
        slug = tk.get("slug") if isinstance(tk, dict) else getattr(tk, "slug", None) or tk
        table.add_row(str(slug), str(a.get("status")), str(a.get("user_id")), str(a.get("id"))[:12])
    console.print(table)
    backend = cfg.resolve_backend()
    console.print(f"\n[bold]LLM backend:[/] {backend}  ({'ready' if cfg.has_llm() else 'NOT READY'})")
    if backend == "kiro_cli":
        console.print(f"[bold]KIRO_API_KEY:[/] {'set' if cfg.kiro_api_key else 'MISSING'}  model: {cfg.kiro_model}")
    else:
        console.print(f"[bold]ANTHROPIC_API_KEY:[/] {'set' if cfg.has_anthropic() else 'MISSING'}")
    console.print(f"[bold]user_id:[/] {cfg.user_id}")
    return 0


def cmd_auth(cfg: Config, args: argparse.Namespace) -> int:
    c = _client(cfg)
    try:
        url = c.authorize(args.toolkit)
    except Exception as exc:
        msg = str(exc)
        if "Default auth config not found" in msg or "use_custom_auth" in msg:
            console.print(Panel.fit(
                f"[yellow]No managed auth for [bold]{args.toolkit}[/].[/yellow]\n\n"
                "Open the Composio dashboard, add an auth config with your own API key,\n"
                "then come back and run this command again. Direct link:\n\n"
                f"[link]https://dashboard.composio.dev/[/link]\n\n"
                f"Original error:\n{msg[:500]}",
                title="Composio auth (manual setup needed)",
            ))
            return 1
        raise
    console.print(Panel.fit(
        f"Open this URL once to connect [bold]{args.toolkit}[/]:\n\n[link]{url}[/link]",
        title="Composio auth",
    ))
    return 0


def cmd_discover(cfg: Config, args: argparse.Namespace) -> int:
    c = _client(cfg)
    scout = CompetitorScout(c)
    competitors = scout.discover(niche=args.niche, n=args.n)
    table = Table(title=f"Competitors for: {args.niche}")
    for col in ("handle", "platform", "url", "notes"):
        table.add_column(col)
    for cm in competitors:
        table.add_row(cm.handle, cm.platform, cm.profile_url, (cm.notes or "")[:60])
    console.print(table)
    return 0


def cmd_scroll(cfg: Config, args: argparse.Namespace) -> int:
    c = _client(cfg)
    sc = IGScroller(c)
    prof = sc.scroll(args.handle, top_k=args.top)
    if prof.error:
        console.print(f"[red]{prof.error}[/red]")
        return 1
    console.print(Panel.fit(
        f"[bold]{prof.handle}[/]  followers: {prof.follower_count}\n{prof.bio}",
        title="IG profile",
    ))
    table = Table(title=f"Top {args.top} reels (by visible engagement)")
    for col in ("url", "views", "likes", "comments", "caption"):
        table.add_column(col)
    for r in prof.reels:
        table.add_row(
            str(r.get("url", ""))[:80],
            str(r.get("views", "")),
            str(r.get("likes", "")),
            str(r.get("comments", "")),
            (r.get("caption") or "")[:80],
        )
    console.print(table)
    return 0


def cmd_analyze(cfg: Config, args: argparse.Namespace) -> int:
    c = _client(cfg)
    intel = VideoIntel(c)
    facts = intel.fetch(args.url)
    _print_facts(facts)
    if not facts.has_text():
        console.print("[yellow]No transcript or caption — can't analyze.[/yellow]")
        return 1
    if not cfg.has_llm():
        console.print("[yellow]No LLM backend (set KIRO_API_KEY or ANTHROPIC_API_KEY) to run hook analysis.[/yellow]")
        return 0
    ana = HookAnalyzer(cfg).analyze(facts)
    console.print(Panel(json.dumps(ana.raw, indent=2), title=f"Analysis (score {ana.score})"))
    return 0


def _gather(cfg: Config, urls: list[str]) -> list[tuple[VideoFacts, Any]]:
    c = _client(cfg)
    intel = VideoIntel(c, watch=True)
    analyzer = HookAnalyzer(cfg)
    pairs: list[tuple[VideoFacts, Any]] = []
    for url in urls:
        console.print(f"[cyan]→ fetching[/cyan] {url}")
        facts = intel.fetch(url)
        if facts.error:
            console.print(f"  [yellow]firecrawl: {facts.error}[/yellow]")
        if facts.watch and facts.watch.error:
            console.print(f"  [yellow]watch: {facts.watch.error}[/yellow]")
        if facts.has_visuals():
            console.print(
                f"  [green]watched[/green] {facts.duration_seconds}s · "
                f"{len(facts.watch.hook_frames)} hook frames · "
                f"{len(facts.watch.scene_frames)} scene frames"
            )
        if not facts.has_text() and not facts.has_visuals():
            console.print("  [yellow]skipped (no text + no visuals)[/yellow]")
            continue
        ana = analyzer.analyze(facts)
        pairs.append((facts, ana))
        console.print(
            f"  hook: {ana.hook_text!r}"
            + (f"  visual: {ana.visual_hook!r}" if ana.visual_hook else "")
            + f"  score: {ana.score}"
        )
    return pairs


def cmd_generate(cfg: Config, args: argparse.Namespace) -> int:
    if not cfg.has_llm():
        console.print("[red]No LLM backend — set KIRO_API_KEY or ANTHROPIC_API_KEY.[/red]")
        return 1
    _nudge_style_setup()
    pillar = _resolve_pillar(args.pillar)
    style = StyleProfile.load()
    pairs = _gather(cfg, args.url)
    engine = ScriptEngine(cfg)
    script = engine.generate(pairs, custom_topic=args.topic, pillar=pillar, style=style)
    if args.spice:
        script = engine.apply_spice(script)
    script = engine.critique(script, style=style)
    _print_script(script)
    return 0


def cmd_iterate(cfg: Config, args: argparse.Namespace) -> int:
    if not cfg.has_llm():
        console.print("[red]No LLM backend — set KIRO_API_KEY or ANTHROPIC_API_KEY.[/red]")
        return 1
    _nudge_style_setup()
    pillar = _resolve_pillar(args.pillar)
    pairs = _gather(cfg, args.url)
    engine = ScriptEngine(cfg)
    history = engine.iterate(
        pairs,
        rounds=args.rounds,
        target_score=args.target,
        custom_topic=args.topic,
        pillar=pillar,
    )
    for s in history:
        console.print(f"\n[bold cyan]── iteration {s.iteration}  score {s.score} ──[/bold cyan]")
        _print_script(s, show_critique=True)
    best = max(history, key=lambda s: s.score)
    console.print(f"\n[bold green]BEST: iteration {best.iteration}, score {best.score}[/bold green]")
    return 0


def _nudge_style_setup() -> None:
    s = StyleProfile.load()
    if not s.is_set():
        console.print(Panel.fit(
            "[yellow]No style profile saved yet.[/yellow]\n"
            "Scripts will use a generic AI-website fallback voice.\n\n"
            "Lock in your real voice (recommended, takes 2 min):\n"
            "  [bold]python -m virality.cli setup-style[/bold]",
            title="heads up",
        ))


def cmd_pillars(_cfg: Config, _args: argparse.Namespace) -> int:
    table = Table(title="The 8 content pillars")
    for col in ("id", "name", "tagline", "why"):
        table.add_column(col)
    for p in load_pillars():
        table.add_row(str(p.id), p.name, p.tagline, p.why_it_works[:60])
    console.print(table)
    style = StyleProfile.load()
    if style.is_set():
        console.print(Panel(style.as_prompt_block(), title="Your saved style"))
    else:
        console.print("[yellow]No style profile yet. Run `setup-style` to lock in your voice.[/yellow]")
    return 0


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or default


def _ask_list(prompt: str, default: list[str]) -> list[str]:
    raw = _ask(f"{prompt} (comma-separated)", ", ".join(default))
    return [x.strip() for x in raw.split(",") if x.strip()]


def cmd_setup_style(_cfg: Config, _args: argparse.Namespace) -> int:
    cur = StyleProfile.load()
    console.print(Panel.fit(
        "I'll ask 10 quick questions to lock in your voice + avatar. "
        "Press enter to keep the current value.\n\n"
        "[bold]Avatar matters most[/]: per the Callaway algorithm model, IG only "
        "cascade-boosts you when EVERY reel serves the same narrow viewer. "
        "Pick one, lock it in, never drift.",
        title="setup-style",
    ))
    cur.creator_name = _ask("Your name / handle", cur.creator_name or "@manoshranjan66")
    cur.niche_specifics = _ask(
        "What you sell (be specific — price + deliverable + customer)",
        cur.niche_specifics or "$1k-3k AI websites + Meta ads automation for local businesses",
    )
    cur.target_audience = _ask(
        "Who you want watching (broad)",
        cur.target_audience or "non-technical small-business owners and aspiring AI agency owners",
    )
    cur.avatar = _ask(
        "LOCKED AVATAR — the SINGLE viewer every reel must serve "
        "(name + age + situation + pain). Be ridiculously specific",
        cur.avatar or (
            "Mike, 38, owns a 2-truck plumbing biz, losing leads to voicemail, "
            "scared of tech but desperate for more jobs"
        ),
    )
    cur.voice_tone = _ask(
        "Voice / tone in 5-8 words",
        cur.voice_tone or "blunt, energetic, no fluff, slightly cocky",
    )
    cur.do_say = _ask_list(
        "Phrases you LIKE saying",
        cur.do_say or ["steal this", "watch this", "the play is", "no fluff"],
    )
    cur.do_not_say = _ask_list(
        "Words/phrases you NEVER say",
        cur.do_not_say or ["leverage", "synergy", "in the realm of", "embark", "delve"],
    )
    cur.cta_style = _ask(
        "CTA style",
        cur.cta_style or "Comment one keyword (like 'PLAYBOOK') for a free DM with the build",
    )
    cur.signature_lines = _ask_list(
        "Catchphrases / sign-offs (optional)",
        cur.signature_lines or [],
    )
    grade_raw = _ask("Reading level (grade)", str(cur.grade_level or 5))
    try:
        cur.grade_level = int(grade_raw)
    except ValueError:
        cur.grade_level = 5
    path = cur.save()
    console.print(f"[green]saved → {path}[/green]")
    console.print(Panel(cur.as_prompt_block(), title="Locked-in style"))
    return 0


def _resolve_pillar(args_pillar: str | None):
    if not args_pillar:
        return None
    return get_pillar(args_pillar)


def _scroll_handles(cfg: Config, handles: list[str], top: int) -> list[str]:
    """Scroll N IG profiles, return the top reel URLs across all of them."""
    c = _client(cfg)
    sc = IGScroller(c)
    all_reels: list[tuple[int, str]] = []
    for h in handles:
        prof = sc.scroll(h, top_k=top)
        if prof.error:
            console.print(f"[yellow]{h}: {prof.error}[/yellow]")
            continue
        console.print(f"[green]{prof.handle}[/green]: {len(prof.reels)} reels")
        for r in prof.reels:
            score = (r.get("views") or 0) + (r.get("likes") or 0) * 5
            url = r.get("url", "")
            if url:
                all_reels.append((score, url))
    all_reels.sort(reverse=True)
    return [u for _, u in all_reels]
    """Scroll N IG profiles, return the top reel URLs across all of them."""
    c = _client(cfg)
    sc = IGScroller(c)
    all_reels: list[tuple[int, str]] = []
    for h in handles:
        prof = sc.scroll(h, top_k=top)
        if prof.error:
            console.print(f"[yellow]{h}: {prof.error}[/yellow]")
            continue
        console.print(f"[green]{prof.handle}[/green]: {len(prof.reels)} reels")
        for r in prof.reels:
            score = (r.get("views") or 0) + (r.get("likes") or 0) * 5
            url = r.get("url", "")
            if url:
                all_reels.append((score, url))
    all_reels.sort(reverse=True)
    return [u for _, u in all_reels]


def _maybe_push_notebook(notebook_title: str | None, pairs) -> None:
    if not notebook_title or not pairs:
        return
    if not nlm_available():
        console.print(
            "[yellow]--notebook set but `nlm` CLI not on PATH. "
            "Install with `uv tool install notebooklm-mcp-cli` and run `nlm login`.[/yellow]"
        )
        return
    console.print(f"[cyan]→ pushing {len(pairs)} reels to NotebookLM: {notebook_title}[/cyan]")
    res = push_to_notebook(notebook_title, pairs)
    if res.error:
        console.print(f"[yellow]NotebookLM: {res.error}[/yellow]")
    if res.sources_added:
        console.print(
            f"[green]NotebookLM:[/green] added {res.sources_added} source(s) "
            f"to notebook {res.notebook_id}"
        )


def cmd_audit(cfg: Config, args: argparse.Namespace) -> int:
    """Scroll a handle and run hook analysis on each top reel."""
    if not cfg.has_llm():
        console.print("[red]No LLM backend — set KIRO_API_KEY or ANTHROPIC_API_KEY.[/red]")
        return 1
    urls = _scroll_handles(cfg, [args.handle], args.top)
    if not urls:
        return 1
    pairs = _gather(cfg, urls)
    table = Table(title=f"{args.handle} — top reel scorecard")
    for col in ("score", "hook_type", "topic", "url", "hook"):
        table.add_column(col)
    for facts, ana in pairs:
        table.add_row(
            str(ana.score),
            ana.hook_type,
            ana.topic[:30],
            facts.url[-40:],
            (ana.hook_text or "")[:60],
        )
    console.print(table)
    _maybe_push_notebook(args.notebook, pairs)
    return 0


def cmd_mine(cfg: Config, args: argparse.Namespace) -> int:
    """Scroll several competitors, mine their best reels, write a fresh script."""
    if not cfg.has_llm():
        console.print("[red]No LLM backend — set KIRO_API_KEY or ANTHROPIC_API_KEY.[/red]")
        return 1
    _nudge_style_setup()
    pillar = _resolve_pillar(args.pillar)
    urls = _scroll_handles(cfg, args.handle, args.per_creator)
    urls = urls[: args.max_videos]
    console.print(f"[cyan]mining {len(urls)} top reels across {len(args.handle)} creators[/cyan]")
    pairs = _gather(cfg, urls)
    if not pairs:
        console.print(
            "[yellow]No competitor reels could be scraped "
            "(Instagram blocks anonymous scraping; reconnect Apify or provide "
            "reel URLs + IG cookies for live data).[/yellow]"
        )
        console.print(
            "[cyan]Falling back to writing a fresh script from your topic/pillar "
            "and locked style.[/cyan]"
        )
    else:
        _maybe_push_notebook(args.notebook, pairs)
    engine = ScriptEngine(cfg)
    history = engine.iterate(
        pairs,
        rounds=args.rounds,
        target_score=args.target,
        custom_topic=args.topic,
        pillar=pillar,
    )
    for s in history:
        console.print(f"\n[bold cyan]── iteration {s.iteration}  score {s.score} ──[/bold cyan]")
        _print_script(s, show_critique=True)
    best = max(history, key=lambda s: s.score)
    console.print(f"\n[bold green]BEST: iteration {best.iteration}, score {best.score}[/bold green]")
    return 0


def cmd_voices(cfg: Config, _args: argparse.Namespace) -> int:
    from .tts import list_voices
    voices = list_voices(cfg)
    table = Table(title="ElevenLabs voices")
    for col in ("name", "category", "voice_id"):
        table.add_column(col)
    for v in voices:
        table.add_row(v.name, v.category, v.voice_id)
    console.print(table)
    console.print(
        "\n[cyan]Set the one you want in elevenlabs.env: "
        "ELEVENLABS_VOICE_ID=<voice_id>[/cyan]"
    )
    return 0


def cmd_clone_voice(cfg: Config, args: argparse.Namespace) -> int:
    from .tts import clone_voice
    vid = clone_voice(cfg, name=args.name, sample_paths=args.sample, description=args.description or "")
    console.print(Panel.fit(
        f"[green]Cloned voice created.[/green]\n\nvoice_id: [bold]{vid}[/bold]\n\n"
        f"Add it to elevenlabs.env:\n  ELEVENLABS_VOICE_ID={vid}",
        title="Instant Voice Clone",
    ))
    return 0


def cmd_narrate(cfg: Config, args: argparse.Namespace) -> int:
    from .tts import narrate, script_to_speech_text, humanize_for_tts
    if args.file:
        raw = Path(args.file).read_text()
        text = script_to_speech_text(raw) if args.clean else raw
    else:
        text = args.text or ""
    if not text.strip():
        console.print("[red]Nothing to narrate. Pass --file or --text.[/red]")
        return 1
    if args.humanize:
        console.print("[cyan]→ humanizing script (pauses, breaths, pronunciation)…[/cyan]")
        text = humanize_for_tts(cfg, text)
        console.print(Panel(text, title="performance script"))
    out = args.out or "content/audio/narration.mp3"
    console.print(f"[cyan]→ narrating {len(text)} chars → {out}[/cyan]")
    path = narrate(cfg, text=text, out_path=out, voice_id=args.voice or "",
                   speed=args.speed, model_id=args.model or "")
    console.print(f"[green]saved → {path}[/green]")
    return 0


def cmd_swipe(cfg: Config, args: argparse.Namespace) -> int:
    """Swipe file: ingest viral videos, reverse-engineer, dashboard, analyze."""
    from . import swipe as sw
    action = args.swipe_action

    if action == "add":
        entries = sw.load_store()
        for url in args.url or []:
            console.print(f"[cyan]→ ingesting[/cyan] {url}")
            s = sw.ingest_url(cfg, url)
            if not s.transcript and not s.views:
                console.print(f"  [yellow]couldn't pull data (private/blocked?). Stored URL only.[/yellow]")
            s = sw.enrich(cfg, s)
            entries = [e for e in entries if e.get("url") != url]  # de-dupe
            entries.append(sw.asdict(s) if hasattr(sw, "asdict") else s.__dict__)
            console.print(f"  [green]{s.views} views[/green] · hook: {s.hook[:70]}")
        # dataclass asdict
        from dataclasses import asdict as _ad
        entries = [e if isinstance(e, dict) else _ad(e) for e in entries]
        path = sw.save_store(entries)
        console.print(f"[green]saved {len(entries)} entries → {path}[/green]")
        return 0

    if action == "list":
        entries = sw.load_store()
        table = Table(title=f"Swipe file ({len(entries)} videos)")
        for col in ("views", "creator", "hook", "format"):
            table.add_column(col)
        for e in sorted(entries, key=lambda x: x.get("views", 0), reverse=True):
            table.add_row(str(e.get("views", 0)), (e.get("creator", "") or "")[:20],
                          (e.get("hook", "") or "")[:60], e.get("format", ""))
        console.print(table)
        return 0

    if action == "dashboard":
        path = sw.build_dashboard(sw.load_store())
        console.print(f"[green]dashboard → {path}[/green] (open in a browser)")
        return 0

    if action == "analyze":
        entries = sw.load_store()
        if not entries:
            console.print("[yellow]No swipe entries yet. Add some: swipe add -u <url>[/yellow]")
            return 1
        md = sw.analyze_patterns(cfg, entries)
        out = Path("../content/swipe_playbook.md")
        out.write_text(f"# Viral Playbook (reverse-engineered from {len(entries)} winners)\n\n{md}\n")
        console.print(f"[green]playbook → {out}[/green]")
        console.print(Panel(Markdown(md[:1500]), title="playbook (preview)"))
        return 0

    console.print("[red]Unknown swipe action.[/red]")
    return 1


def cmd_brain(cfg: Config, args: argparse.Namespace) -> int:
    """The Brain: find today's most viral AI topics and clone them into scripts."""
    from . import trend_brain
    if not cfg.has_llm():
        console.print("[red]No LLM backend (set KIRO_API_KEY).[/red]")
        return 1
    console.print("[cyan]🧠 pulling today's freshest AI headlines…[/cyan]")
    queries = args.query or None
    stories = trend_brain.rank_stories(
        trend_brain.fetch_headlines(queries or trend_brain.DEFAULT_QUERIES),
        limit=args.scan,
    )
    if not stories:
        console.print("[yellow]No headlines fetched (network?). Try again.[/yellow]")
        return 1
    console.print(f"[green]scanned {len(stories)} trending stories. Reverse-engineering the top {args.n}…[/green]")
    picks = trend_brain.analyze_and_script(cfg, stories, n=args.n)
    reels = picks.get("picks", []) if isinstance(picks, dict) else []
    if not reels:
        console.print("[yellow]Brain returned no picks.[/yellow]")
        return 1

    from datetime import date
    day = date.today().isoformat()
    lines = [f"# 🧠 Brain Drop — {day}",
             "\nToday's most viral-worthy AI topics, reverse-engineered into ready reels.\n",
             "## Trending stories scanned (real, last 48h)\n"]
    for s in stories[:12]:
        lines.append(f"- {s.title} — *{s.source}* ({s.hits} outlet[s])")
    lines.append("\n---\n")
    for i, r in enumerate(reels, 1):
        lines.append(f"## Reel {i} — {r.get('topic','')}\n")
        lines.append(f"- **Pillar:** {r.get('pillar','')}")
        lines.append(f"- **Why it'll pop:** {r.get('why_viral','')}\n")
        lines.append(f"**HOOK:** {r.get('hook','')}\n")
        lines.append(f"**SCRIPT:**\n```\n{r.get('script','')}\n```\n")
        ost = r.get('onscreen_text') or []
        lines.append("**On-screen text:** " + " · ".join(ost) + "\n")
        lines.append(f"**CTA:** {r.get('cta','')}\n")
        lines.append(f"**Caption:** {r.get('caption','')}\n")
        lines.append("---\n")

    out = Path(args.out) if args.out else Path(f"../content/brain/{day}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    console.print(f"[green]🧠 saved {len(reels)} viral-ready reels → {out}[/green]")
    for i, r in enumerate(reels, 1):
        console.print(f"  {i}. [{r.get('pillar','')}] {r.get('hook','')[:80]}")
    return 0


def _print_facts(f: VideoFacts) -> None:
    body = (
        f"platform: {f.platform}\nauthor: {f.author}\ntitle: {f.title}\n"
        f"views: {f.views}  likes: {f.likes}  comments: {f.comments}\n"
        f"caption: {(f.caption or '')[:160]}\n\n"
        f"transcript ({len(f.transcript)} chars):\n{f.transcript[:600]}"
    )
    console.print(Panel(body, title=f.url))


def _print_script(s: Script, show_critique: bool = False) -> None:
    md = (
        f"### Hook\n> {s.hook}\n\n"
        f"### Script\n```\n{s.script}\n```\n\n"
        f"### CTA\n{s.cta}\n\n"
        f"### B-roll\n- " + "\n- ".join(s.b_roll or ["(none)"]) + "\n\n"
        f"### Titles\n- " + "\n- ".join(s.title_options or ["(none)"]) + "\n\n"
        f"### Caption\n{s.caption}\n"
    )
    console.print(Panel(Markdown(md), title=f"Script (score {s.score})"))
    if show_critique and s.critique:
        console.print(Panel(json.dumps(s.critique, indent=2), title="Critique"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="virality")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")

    a = sub.add_parser("auth", help="Print Composio redirect URL for a toolkit")
    a.add_argument("toolkit")

    d = sub.add_parser("discover")
    d.add_argument("--niche", default="ai automation tools")
    d.add_argument("-n", type=int, default=10)

    sc = sub.add_parser("scroll")
    sc.add_argument("handle")
    sc.add_argument("--top", type=int, default=5)

    an = sub.add_parser("analyze")
    an.add_argument("url")

    g = sub.add_parser("generate")
    g.add_argument("-u", "--url", action="append", required=True)
    g.add_argument("--topic", default=None)
    g.add_argument("--pillar", default=None, help="Pillar id (1-8) or name")
    g.add_argument("--spice", action="store_true", default=True)
    g.add_argument("--no-spice", dest="spice", action="store_false")

    it = sub.add_parser("iterate")
    it.add_argument("-u", "--url", action="append", required=True)
    it.add_argument("-r", "--rounds", type=int, default=3)
    it.add_argument("--target", type=int, default=85)
    it.add_argument("--topic", default=None)
    it.add_argument("--pillar", default=None, help="Pillar id (1-8) or name")

    au = sub.add_parser("audit", help="Scroll a handle and score its top reels")
    au.add_argument("handle")
    au.add_argument("--top", type=int, default=5)
    au.add_argument("--notebook", default=None,
                    help="If set, push every analyzed reel into this NotebookLM notebook (created if missing)")

    mn = sub.add_parser("mine", help="Mine N competitors' top reels, write a fresh script")
    mn.add_argument("handle", nargs="+")
    mn.add_argument("--per-creator", type=int, default=3)
    mn.add_argument("--max-videos", type=int, default=8)
    mn.add_argument("-r", "--rounds", type=int, default=2)
    mn.add_argument("--target", type=int, default=85)
    mn.add_argument("--topic", default=None)
    mn.add_argument("--pillar", default=None, help="Pillar id (1-8) or name")
    mn.add_argument("--notebook", default=None,
                    help="If set, push every analyzed reel into this NotebookLM notebook (created if missing)")

    sub.add_parser("pillars", help="Show the 8 content pillars + your saved style")
    sub.add_parser("setup-style", help="Lock in your voice (asked once, reused forever)")

    sw_p = sub.add_parser("swipe", help="Swipe file: ingest viral videos + reverse-engineer them")
    sw_sub = sw_p.add_subparsers(dest="swipe_action", required=True)
    sw_add = sw_sub.add_parser("add", help="Ingest a viral video URL (pulls real views + transcript)")
    sw_add.add_argument("-u", "--url", action="append", required=True)
    sw_sub.add_parser("list", help="List swipe file entries")
    sw_sub.add_parser("dashboard", help="Build the HTML dashboard")
    sw_sub.add_parser("analyze", help="Reverse-engineer patterns into a playbook")

    br = sub.add_parser("brain", help="Find today's most viral AI topics and clone them into scripts")
    br.add_argument("-n", type=int, default=5, help="How many reels to generate")
    br.add_argument("--scan", type=int, default=20, help="How many trending stories to scan")
    br.add_argument("--query", action="append", help="Custom search query (repeatable)")
    br.add_argument("--out", default=None, help="Output md path (default content/brain/DATE.md)")

    sub.add_parser("voices", help="List ElevenLabs voices on your account")

    cv = sub.add_parser("clone-voice", help="Create an Instant Voice Clone from audio samples")
    cv.add_argument("--name", required=True, help="Name for the cloned voice")
    cv.add_argument("--sample", action="append", required=True,
                    help="Path to a clean audio sample of you talking (repeatable)")
    cv.add_argument("--description", default="")

    nr = sub.add_parser("narrate", help="Turn a script (file or text) into an MP3 via ElevenLabs")
    nr.add_argument("--file", default=None, help="Path to a script/day markdown file")
    nr.add_argument("--text", default=None, help="Raw text to narrate")
    nr.add_argument("--out", default=None, help="Output mp3 path (default content/audio/narration.mp3)")
    nr.add_argument("--voice", default=None, help="Voice id override")
    nr.add_argument("--speed", type=float, default=1.0)
    nr.add_argument("--model", default=None, help="ElevenLabs model id (default: expressive, auto-fallback)")
    nr.add_argument("--clean", action="store_true", default=True,
                    help="Strip markdown/labels so only spoken words are narrated")
    nr.add_argument("--raw", dest="clean", action="store_false", help="Narrate the file verbatim")
    nr.add_argument("--humanize", action="store_true", default=True,
                    help="Rewrite with natural pauses, breaths, and fixed pronunciation (default on)")
    nr.add_argument("--no-humanize", dest="humanize", action="store_false",
                    help="Narrate the text as-is, no performance rewrite")

    args = p.parse_args(argv)
    cfg = Config.load()

    handlers = {
        "status": cmd_status,
        "auth": cmd_auth,
        "discover": cmd_discover,
        "scroll": cmd_scroll,
        "analyze": cmd_analyze,
        "generate": cmd_generate,
        "iterate": cmd_iterate,
        "audit": cmd_audit,
        "mine": cmd_mine,
        "pillars": cmd_pillars,
        "setup-style": cmd_setup_style,
        "voices": cmd_voices,
        "clone-voice": cmd_clone_voice,
        "narrate": cmd_narrate,
        "brain": cmd_brain,
        "swipe": cmd_swipe,
    }
    return handlers[args.cmd](cfg, args)


if __name__ == "__main__":
    sys.exit(main())
