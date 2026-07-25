#!/usr/bin/env node
// virality-agent (TS) — Tool Router edition.
// Commands:
//   status                       confirm config + Composio session
//   scroll <handle> [--top N]    pull a creator's top reels
//   analyze <reel-url>           Callaway-score a single reel
//   audit <handle> [--top N]     scroll + score every top reel
//   mine <h1> <h2> ...           multi-creator → script + score
import { loadConfig } from "./config.js";
import { getToolRouterSession } from "./composio.js";
import {
  scrollProfile,
  fetchReel,
  analyzeReel,
  generateScript,
  critiqueScript,
} from "./flows.js";
import { loadStyle } from "./style.js";

function parseArgs(argv: string[]): { cmd: string; positional: string[]; flags: Record<string, string> } {
  const [cmd, ...rest] = argv;
  const positional: string[] = [];
  const flags: Record<string, string> = {};
  for (let i = 0; i < rest.length; i++) {
    const a = rest[i];
    if (a.startsWith("--")) {
      const key = a.slice(2);
      const val = rest[i + 1] && !rest[i + 1].startsWith("--") ? rest[++i] : "true";
      flags[key] = val;
    } else {
      positional.push(a);
    }
  }
  return { cmd, positional, flags };
}

function printJSON(label: string, obj: any): void {
  console.log(`\n=== ${label} ===`);
  console.log(JSON.stringify(obj, null, 2));
}

async function cmdStatus() {
  const cfg = loadConfig();
  console.log("Config:");
  console.log(`  composio key:       ${cfg.composioApiKey.slice(0, 8)}...`);
  console.log(`  anthropic key:      ${cfg.anthropicApiKey ? "set" : "MISSING"}`);
  console.log(`  anthropic base url: ${cfg.anthropicBaseUrl || "(default Anthropic)"}`);
  console.log(`  model:              ${cfg.claudeModel}`);
  console.log(`  user_id:            ${cfg.userId}`);
  console.log(`  ig cookies:         ${cfg.igCookiesFile || "(none — visual analysis off)"}`);
  console.log("\nOpening Composio Tool Router session...");
  const session = await getToolRouterSession(cfg);
  const tools = await session.tools();
  console.log(`  tools available:    ${Array.isArray(tools) ? tools.length : "?"}`);
  const style = loadStyle();
  console.log(`\nLocked avatar:\n  ${style.avatar}`);
}

async function cmdScroll(positional: string[], flags: Record<string, string>) {
  const cfg = loadConfig();
  const handle = positional[0];
  if (!handle) throw new Error("usage: scroll <handle> [--top N]");
  const top = parseInt(flags.top || "5", 10);
  console.log(`→ scrolling @${handle.replace(/^@/, "")} (top ${top})`);
  const prof = await scrollProfile(cfg, handle, top);
  printJSON("profile", prof);
}

async function cmdAnalyze(positional: string[]) {
  const cfg = loadConfig();
  const url = positional[0];
  if (!url) throw new Error("usage: analyze <reel-url>");
  console.log(`→ fetching ${url}`);
  const facts = await fetchReel(cfg, url);
  printJSON("facts", facts);
  console.log("\n→ Callaway scoring...");
  const ana = await analyzeReel(cfg, facts);
  printJSON("analysis", ana);
}

async function cmdAudit(positional: string[], flags: Record<string, string>) {
  const cfg = loadConfig();
  const handle = positional[0];
  if (!handle) throw new Error("usage: audit <handle> [--top N]");
  const top = parseInt(flags.top || "5", 10);
  console.log(`→ scrolling @${handle.replace(/^@/, "")}`);
  const prof = await scrollProfile(cfg, handle, top);
  if (!prof.reels.length) {
    console.log("(no reels found — Firecrawl probably needs a Composio auth config)");
    return;
  }
  const rows: any[] = [];
  for (const r of prof.reels) {
    if (!r.url) continue;
    console.log(`  → analyzing ${r.url}`);
    const facts = await fetchReel(cfg, r.url);
    const ana = await analyzeReel(cfg, facts);
    rows.push({
      url: r.url,
      score: ana?.virality_score?.score_0_100,
      hook_type: ana?.hook?.hook_type,
      hook: ana?.hook?.first_3_seconds,
      audience_match: ana?.audience_match?.score_0_25,
      drift: ana?.audience_match?.topic_drift_warning || "",
      topic: ana?.topic,
    });
  }
  printJSON("scorecard", rows);
}

async function cmdMine(positional: string[], flags: Record<string, string>) {
  const cfg = loadConfig();
  if (!positional.length) throw new Error("usage: mine <h1> <h2> ... [--per-creator N] [--topic ...]");
  const perCreator = parseInt(flags["per-creator"] || "3", 10);
  const max = parseInt(flags["max-videos"] || "8", 10);
  const topic = flags.topic || null;

  const allUrls: { url: string; score: number }[] = [];
  for (const h of positional) {
    console.log(`→ scrolling @${h.replace(/^@/, "")}`);
    const prof = await scrollProfile(cfg, h, perCreator);
    for (const r of prof.reels) {
      if (!r.url) continue;
      const score = (r.views || 0) + (r.likes || 0) * 5;
      allUrls.push({ url: r.url, score });
    }
  }
  allUrls.sort((a, b) => b.score - a.score);
  const urls = allUrls.slice(0, max).map((x) => x.url);
  console.log(`→ analyzing ${urls.length} reels`);

  const pairs: Array<{ facts: any; analysis: any }> = [];
  for (const url of urls) {
    const facts = await fetchReel(cfg, url);
    const analysis = await analyzeReel(cfg, facts);
    pairs.push({ facts, analysis });
  }

  console.log("→ generating script");
  const script = await generateScript(cfg, pairs, topic);
  printJSON("script", script);

  console.log("→ critiquing");
  const critique = await critiqueScript(cfg, {
    hook: script?.hook || "",
    script: script?.script || "",
    cta: script?.cta || "",
  });
  printJSON("critique", critique);
}

async function main() {
  const { cmd, positional, flags } = parseArgs(process.argv.slice(2));
  if (!cmd) {
    console.log("commands: status | scroll | analyze | audit | mine");
    process.exit(1);
  }
  const handlers: Record<string, () => Promise<void>> = {
    status: cmdStatus,
    scroll: () => cmdScroll(positional, flags),
    analyze: () => cmdAnalyze(positional),
    audit: () => cmdAudit(positional, flags),
    mine: () => cmdMine(positional, flags),
  };
  const h = handlers[cmd];
  if (!h) {
    console.error(`unknown command: ${cmd}`);
    process.exit(1);
  }
  await h();
}

main().catch((e) => {
  console.error("ERROR:", e?.message || e);
  process.exit(1);
});
