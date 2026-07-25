// Loads the algo_bible.md once, exposes it as a constant for prompt injection.
// The bible is the synthesis of Mosseri (40%) + Hormozi 1M (30%) + Hormozi 2026 (20%) + Brock (10%).
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const BIBLE_PATH = join(__dirname, "..", "research", "algo_bible.md");

let _bible: string | null = null;

export function getAlgoBible(): string {
  if (_bible !== null) return _bible;
  try {
    _bible = readFileSync(BIBLE_PATH, "utf-8");
  } catch {
    _bible = "";
  }
  return _bible;
}

// A compact subset for prompts where the full ~3500-word bible is too heavy.
export function getAlgoBibleTLDR(): string {
  const full = getAlgoBible();
  if (!full) return "";
  // Pull TL;DR through the rubric, drop the long quotable-lines tail.
  const tldrStart = full.indexOf("## TL;DR");
  const rubricEnd = full.indexOf("## Quotable lines");
  if (tldrStart === -1) return full.slice(0, 4000);
  if (rubricEnd === -1) return full.slice(tldrStart);
  return full.slice(tldrStart, rubricEnd).trim();
}
