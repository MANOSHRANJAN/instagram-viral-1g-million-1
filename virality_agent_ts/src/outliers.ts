// Outlier detector — compares each reel against the creator's historical median.
// Flags views > 5x median (last N reels) → outlier_queue.json for deep analysis.
import { existsSync, readFileSync, writeFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import type { ScoutedProfile, ScoutedReel } from "./scout.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const SCOUT_DIR = join(ROOT, "scout");
const QUEUE_PATH = join(ROOT, "outlier_queue.json");
const PROCESSED_PATH = join(ROOT, "outlier_processed.json");

const MULTIPLIER = 5; // views > 5x median = outlier
const MIN_HISTORY = 6; // need at least 6 reels of history before scoring

export interface Outlier {
  handle: string;
  url: string;
  shortcode: string;
  views: number;
  median_views: number;
  multiplier: number;
  caption: string;
  flagged_at: string;
}

function median(nums: number[]): number {
  if (!nums.length) return 0;
  const sorted = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function loadProcessed(): Set<string> {
  if (!existsSync(PROCESSED_PATH)) return new Set();
  try {
    return new Set(JSON.parse(readFileSync(PROCESSED_PATH, "utf-8")) as string[]);
  } catch {
    return new Set();
  }
}

function saveProcessed(processed: Set<string>): void {
  writeFileSync(PROCESSED_PATH, JSON.stringify([...processed], null, 2));
}

function loadQueue(): Outlier[] {
  if (!existsSync(QUEUE_PATH)) return [];
  try {
    return JSON.parse(readFileSync(QUEUE_PATH, "utf-8"));
  } catch {
    return [];
  }
}

function saveQueue(q: Outlier[]): void {
  writeFileSync(QUEUE_PATH, JSON.stringify(q, null, 2));
}

function loadHistory(handle: string): ScoutedProfile[] {
  const p = join(SCOUT_DIR, `${handle}.json`);
  if (!existsSync(p)) return [];
  try {
    return JSON.parse(readFileSync(p, "utf-8"));
  } catch {
    return [];
  }
}

// Flatten all snapshots into a map of unique reels (latest counts win)
function reelMap(history: ScoutedProfile[]): Map<string, ScoutedReel> {
  const m = new Map<string, ScoutedReel>();
  for (const snap of history) {
    for (const r of snap.reels) {
      const prev = m.get(r.shortcode);
      // Keep the latest non-null view count
      if (!prev || (r.views !== null && (prev.views === null || r.views > prev.views))) {
        m.set(r.shortcode, r);
      }
    }
  }
  return m;
}

export function detectOutliersForHandle(handle: string): Outlier[] {
  const history = loadHistory(handle);
  if (history.length === 0) return [];
  const allReels = [...reelMap(history).values()].filter((r) => r.views !== null);
  if (allReels.length < MIN_HISTORY) {
    console.log(`  (${handle}: only ${allReels.length} reels with view counts — need ${MIN_HISTORY} for outlier scoring)`);
    return [];
  }
  const med = median(allReels.map((r) => r.views!));
  if (med < 1000) {
    console.log(`  (${handle}: median ${med} too low — skipping)`);
    return [];
  }

  const flagged: Outlier[] = [];
  for (const r of allReels) {
    if (r.views === null) continue;
    const mult = r.views / med;
    if (mult >= MULTIPLIER) {
      flagged.push({
        handle,
        url: r.url,
        shortcode: r.shortcode,
        views: r.views,
        median_views: med,
        multiplier: Number(mult.toFixed(2)),
        caption: r.caption.slice(0, 300),
        flagged_at: new Date().toISOString(),
      });
    }
  }
  return flagged;
}

export function detectAll(): Outlier[] {
  if (!existsSync(SCOUT_DIR)) {
    console.error(`no scout data — run \`npm run scout\` first`);
    return [];
  }
  const handles = readdirSync(SCOUT_DIR)
    .filter((f) => f.endsWith(".json"))
    .map((f) => f.replace(/\.json$/, ""));

  const processed = loadProcessed();
  const queue = loadQueue();
  const queuedShortcodes = new Set(queue.map((q) => q.shortcode));
  const newOutliers: Outlier[] = [];

  for (const h of handles) {
    const flagged = detectOutliersForHandle(h);
    for (const o of flagged) {
      if (processed.has(o.shortcode) || queuedShortcodes.has(o.shortcode)) continue;
      newOutliers.push(o);
      queue.push(o);
    }
  }

  if (newOutliers.length) {
    saveQueue(queue);
    console.log(`\n✓ ${newOutliers.length} new outlier(s) flagged → outlier_queue.json`);
    for (const o of newOutliers) {
      console.log(`  • @${o.handle}: ${o.views.toLocaleString()} views (${o.multiplier}x median) — ${o.url}`);
    }
  } else {
    console.log("\nno new outliers");
  }
  return newOutliers;
}

export function markProcessed(shortcodes: string[]): void {
  const processed = loadProcessed();
  for (const s of shortcodes) processed.add(s);
  saveProcessed(processed);
  // also drop them from the queue
  const queue = loadQueue().filter((q) => !shortcodes.includes(q.shortcode));
  saveQueue(queue);
}

if (process.argv[1] && process.argv[1].endsWith("outliers.ts")) {
  detectAll();
}
