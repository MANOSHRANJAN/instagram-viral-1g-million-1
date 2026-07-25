// Pattern extractor — reads learned/all.json, asks Claude to find repeating DNA
// across all reels, writes learned/patterns.md (used by the writer for inspiration).
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import Anthropic from "@anthropic-ai/sdk";
import { loadConfig } from "./config.js";
import { getAlgoBible } from "./bible.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const LEARNED_DIR = join(__dirname, "..", "learned");
const ALL_PATH = join(LEARNED_DIR, "all.json");
const PATTERNS_PATH = join(LEARNED_DIR, "patterns.md");

const SYSTEM = `You are a virality pattern detective. You look at N reel analyses
and find the STRUCTURAL DNA that repeats across them. You distinguish surface
similarities from true patterns. You cite which reels (by index) back each pattern.
You always return a single markdown document. No prose outside the document.`;

function buildPrompt(reelData: any[]): string {
  const compact = reelData.map((r, i) => ({
    i,
    url: r.url,
    duration: r.duration_seconds,
    transcript_excerpt: (r.transcript || "").slice(0, 800),
    hook: r.analysis?.hook,
    structure: r.analysis?.structure,
    audience_match: r.analysis?.audience_match,
    attention_25: r.analysis?.attention_25,
    retention_25: r.analysis?.retention_25,
    distribution_25: r.analysis?.distribution_25,
    conversion_25: r.analysis?.conversion_25,
    score: r.analysis?.virality_score?.score_0_100,
    drivers: r.analysis?.virality_score?.drivers,
    leaks: r.analysis?.virality_score?.leaks,
    transferable_angles: r.analysis?.transferable_angles,
  }));

  return `You have ${reelData.length} reel analyses below. Find the structural DNA that repeats.

=== ALGORITHM BIBLE (load-bearing rules to ground your patterns in) ===
${getAlgoBible().slice(0, 6000)}
=== END BIBLE ===

=== REEL ANALYSES (JSON, indexed) ===
${JSON.stringify(compact, null, 2)}
=== END ANALYSES ===

Write a single markdown document called "Learned Patterns" with these sections.
Cite reel indices in brackets like [reel #2, #5] for every pattern you claim.

# Learned Patterns

## Hook Formulas That Repeat
(For each repeating hook formula across the corpus: name it, give 2-3 actual examples with reel indices, explain WHY it works in Bible terms.)

## Structural Skeletons That Repeat
(Hook → ? → ? → ? — what structure repeats? Cite reels.)

## Visual / Cut Patterns
(Cuts every X seconds? Talking head + text overlay? Split screen? Cite reels.)

## SFX / Audio Patterns
(Silent text overlays? Trending audio? Specific BPM? Voiceover-only? Cite reels.)

## Comment / Engagement Driver Patterns
(Keyword DM? Hard stance? Contrarian? "Send this to..." framing? Cite reels.)

## What's Working in THIS Avatar's Niche (vs general virality)
(If the user's locked avatar appears in the analyses, what specifically works for THEM vs generic AI-niche reels?)

## What's NOT Working (consistent leaks)
(Patterns that repeatedly hurt scores across the corpus.)

## 5 Hook Templates the User Can Reuse Tomorrow
(Concrete fill-in-the-blank templates derived from the patterns. Each one cites which reels back it. Each one is rewritten to serve the user's locked avatar, not the original creator's.)

## How the Writer Should Use These Patterns
(One paragraph: when generating 3 script variations, the writer should pick 3 DIFFERENT hook formulas + 3 DIFFERENT structures from the patterns above so the variations are genuinely distinct.)

Be specific. Cite indices. Quote transcripts directly when relevant.`;
}

async function main() {
  if (!existsSync(ALL_PATH)) {
    console.error(`no learned reels yet — run \`npm run learn\` first`);
    process.exit(1);
  }
  const reels: any[] = JSON.parse(readFileSync(ALL_PATH, "utf-8"));
  if (!reels.length) {
    console.error(`learned/all.json is empty`);
    process.exit(1);
  }
  console.log(`extracting patterns across ${reels.length} reels`);

  const cfg = loadConfig();
  const anthropic = new Anthropic({
    apiKey: cfg.anthropicApiKey,
    baseURL: cfg.anthropicBaseUrl || undefined,
  });

  const msg = await anthropic.messages.create({
    model: cfg.claudeModel,
    max_tokens: 6000,
    system: SYSTEM,
    messages: [{ role: "user", content: buildPrompt(reels) }],
  });
  const text = msg.content
    .filter((b: any) => b.type === "text")
    .map((b: any) => b.text)
    .join("\n");

  writeFileSync(PATTERNS_PATH, text);
  console.log(`wrote ${PATTERNS_PATH} (${text.length} chars)`);
}

main().catch((e) => {
  console.error("ERROR:", e?.message || e);
  process.exit(1);
});
