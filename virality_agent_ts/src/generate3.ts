// Generate 3 distinct script variations using learned patterns.
// Each variation must use a DIFFERENT hook formula + structure from the patterns doc.
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import Anthropic from "@anthropic-ai/sdk";
import { loadConfig } from "./config.js";
import { loadStyle, styleAsPromptBlock } from "./style.js";
import { getAlgoBibleTLDR } from "./bible.js";
import { extractJson } from "./agent.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const LEARNED_DIR = join(__dirname, "..", "learned");
const PATTERNS_PATH = join(LEARNED_DIR, "patterns.md");
const SCRIPTS_DIR = join(__dirname, "..", "scripts");

const WRITER_SYSTEM = `You are a short-form Instagram scriptwriter for the AI niche.
You write 30-45 second reel scripts that hook in 3 seconds and never let go.
You ALWAYS write in the creator's own voice (style profile is the source of truth)
and ALWAYS serve the locked avatar — drift on this piece kills cascade boost.
You write to the Algorithm Bible (Mosseri / Hormozi / Hormozi / Brock) AND the
learned patterns from the user's competitive corpus.
You return a single valid JSON object with THREE distinct variations. No prose outside JSON.`;

function buildPrompt(args: { topic: string | null }): string {
  const style = loadStyle();
  const bible = getAlgoBibleTLDR();
  const patterns = existsSync(PATTERNS_PATH) ? readFileSync(PATTERNS_PATH, "utf-8") : "(no learned patterns yet — run `npm run patterns` after `npm run learn`)";

  return `Write THREE distinct Instagram reel script variations (each 30-45s, ~110 words).

=== ALGORITHM BIBLE (load-bearing rules) ===
${bible}
=== END BIBLE ===

=== LEARNED PATTERNS (from competitive corpus, cited) ===
${patterns}
=== END PATTERNS ===

${styleAsPromptBlock(style)}

WRITING RULES (from the Bible)
- Hook: 5-12 words. Negative or numbered framing preferred. Specific number or named entity. Pair with an easy-to-read visual cue.
- "Hammer" line right after hook (proven to land).
- Structure: Hook → Question → Hammer → Example → Explanation (Hormozi 1M skeleton).
- Cuts every 2 seconds (write the b_roll list with that pacing in mind — Brock's rule).
- Body MUST fulfill the hook's promise (Hormozi/MrBeast rule). Hook-body mismatch is a hard fail.
- CTAs: open + mid + end (Hormozi 1M's 3-place inject), OR one extremely strong single.
- Specificity travels (Brock + Hormozi 2026: observable, operational language over emotional words).
- Mosseri: optimize for SEND-WORTHY (would the viewer DM this to one specific friend?), not just shareable.

THREE-VARIATION RULES
- Each variation MUST use a DIFFERENT hook formula from the learned patterns.
- Each variation MUST use a DIFFERENT structural skeleton.
- Each variation must serve the SAME locked avatar (no drift across variations).
- Cite which pattern (by name from patterns.md) each variation is built on.
${args.topic ? `\nFORCED TOPIC: ${args.topic}` : ""}

Return ONE JSON object with this EXACT shape:
{
  "topic": "...",
  "locked_avatar": "(echo back the avatar from the style profile)",
  "variations": [
    {
      "id": "v1",
      "pattern_used": "name of hook formula + skeleton from patterns.md",
      "hook": "first 3 seconds, verbatim — must be 5-12 words",
      "hammer": "the line right after the hook",
      "script": "full ~110-word script with line breaks for delivery",
      "b_roll": ["3-6 visual cues, one per ~2s cut"],
      "sfx_track": ["timed sfx hits — e.g. '0.5s: whoosh', '3.2s: impact'"],
      "caption": "the IG caption with 3-6 hashtags",
      "title_options": ["3 punchy titles under 60 chars"],
      "cta": "the spoken CTA line (matched to creator's CTA style)",
      "music_style_hint": "one phrase — e.g. 'cinematic riser', 'punchy trending hip-hop'",
      "predicted_top_comment": "the single comment most viewers will leave"
    },
    { "id": "v2", ... same shape ... },
    { "id": "v3", ... same shape ... }
  ]
}`;
}

async function main() {
  const topicArgIdx = process.argv.indexOf("--topic");
  const topic = topicArgIdx > 0 ? process.argv[topicArgIdx + 1] : null;

  const cfg = loadConfig();
  if (!cfg.anthropicApiKey) {
    console.error("ANTHROPIC_API_KEY missing");
    process.exit(1);
  }
  if (!existsSync(PATTERNS_PATH)) {
    console.warn(`⚠ no learned patterns yet — variations will be Bible-grounded only.`);
    console.warn(`  run \`npm run learn -- <urls or folder>\` then \`npm run patterns\` for richer scripts.`);
  }

  console.log(`generating 3 variations${topic ? ` (topic: ${topic})` : ""}`);
  const anthropic = new Anthropic({
    apiKey: cfg.anthropicApiKey,
    baseURL: cfg.anthropicBaseUrl || undefined,
  });

  const msg = await anthropic.messages.create({
    model: cfg.claudeModel,
    max_tokens: 5000,
    system: WRITER_SYSTEM,
    messages: [{ role: "user", content: buildPrompt({ topic }) }],
  });
  const text = msg.content
    .filter((b: any) => b.type === "text")
    .map((b: any) => b.text)
    .join("\n");
  const j = extractJson(text);

  mkdirSync(SCRIPTS_DIR, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const outPath = join(SCRIPTS_DIR, `scripts_${stamp}.json`);
  writeFileSync(outPath, JSON.stringify(j, null, 2));
  console.log(`saved → ${outPath}`);
  console.log("\n=== VARIATIONS ===");
  console.log(JSON.stringify(j, null, 2));
}

main().catch((e) => {
  console.error("ERROR:", e?.message || e);
  process.exit(1);
});
