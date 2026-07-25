// Strip VTT timestamps + dedupe lines so we can feed clean text to the framework extractor.
import { readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const RESEARCH = join(__dirname, "..", "research");

const FILES = [
  ["mosseri", "Adam Mosseri (Head of IG)", 40],
  ["hormozi_1m", "Alex Hormozi 1M Followers (Think Media)", 30],
  ["hormozi_strategy", "Alex Hormozi 2026 Social Strategy", 20],
  ["brock", "Brock Johnson (Build Your Tribe)", 10],
  ["mrbeast", "MrBeast 100M views/video", 100], // bonus weight, treat separately
] as const;

function cleanVtt(vtt: string): string {
  const lines = vtt.split("\n");
  const out: string[] = [];
  const seen = new Set<string>();
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith("WEBVTT") || line.startsWith("Kind:") || line.startsWith("Language:")) continue;
    if (/^\d{2}:\d{2}/.test(line)) continue;          // timestamp lines
    if (line.startsWith("NOTE")) continue;
    // strip inline tags <00:00:01.000><c>word</c>
    const stripped = line.replace(/<[^>]+>/g, "").trim();
    if (!stripped) continue;
    if (seen.has(stripped)) continue;
    seen.add(stripped);
    out.push(stripped);
  }
  return out.join(" ");
}

for (const [slug] of FILES) {
  const vtt = readFileSync(join(RESEARCH, `${slug}.en.vtt`), "utf-8");
  const text = cleanVtt(vtt);
  writeFileSync(join(RESEARCH, `${slug}.txt`), text);
  console.log(`${slug}.txt — ${text.length} chars`);
}
