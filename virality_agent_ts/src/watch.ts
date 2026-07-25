// watch.ts — the standing watchman.
// Loop every 2 hours:
//   1. scout each competitor (Playwright)
//   2. detect outliers (views > 5x handle's median)
//   3. for each new outlier → run the existing learn pipeline (yt-dlp + Bible)
//   4. when N new outliers landed → regenerate patterns.md
//   5. log a summary, sleep
//
// Run once:           npx tsx src/watch.ts once
// Run loop:           npx tsx src/watch.ts loop
// Run loop custom:    INTERVAL_MIN=120 npx tsx src/watch.ts loop
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { scoutProfile, appendHistory, loadCompetitors } from "./scout.js";
import { detectAll, markProcessed, type Outlier } from "./outliers.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

const PATTERN_REFRESH_AT = 3; // after this many new outliers analyzed, regenerate patterns
const INTERVAL_MIN = parseInt(process.env.INTERVAL_MIN || "120", 10);

function ts(): string {
  return new Date().toISOString().replace("T", " ").slice(0, 19);
}

function runLearnOnUrl(url: string): boolean {
  console.log(`  → learning ${url}`);
  const r = spawnSync(
    "npx",
    ["tsx", "src/learn.ts", url],
    { cwd: ROOT, stdio: "inherit" }
  );
  return r.status === 0;
}

function refreshPatterns(): boolean {
  console.log("  → regenerating patterns.md");
  const r = spawnSync(
    "npx",
    ["tsx", "src/patterns.ts"],
    { cwd: ROOT, stdio: "inherit" }
  );
  return r.status === 0;
}

async function runOnce(): Promise<void> {
  console.log(`\n[${ts()}] scout cycle`);

  // 1. SCOUT
  const competitors = loadCompetitors();
  console.log(`  • scouting ${competitors.length} competitors`);
  for (const handle of competitors) {
    try {
      const snap = await scoutProfile(handle);
      appendHistory(snap.handle, snap);
      const reelsWithViews = snap.reels.filter((r) => r.views !== null).length;
      console.log(`    ✓ @${handle}: ${snap.reels.length} reels (${reelsWithViews} with view counts)`);
    } catch (e: any) {
      console.log(`    ✗ @${handle}: ${e?.message?.slice(0, 100)}`);
    }
    // gentle delay between profiles to look less bot-y
    await new Promise((r) => setTimeout(r, 4000 + Math.random() * 3000));
  }

  // 2. DETECT
  console.log(`\n  • detecting outliers`);
  const outliers: Outlier[] = detectAll();

  if (!outliers.length) {
    console.log(`[${ts()}] cycle done — no new outliers\n`);
    return;
  }

  // 3. LEARN each new outlier
  const learned: string[] = [];
  for (const o of outliers) {
    if (runLearnOnUrl(o.url)) {
      learned.push(o.shortcode);
    } else {
      console.log(`    ⚠ failed to learn ${o.url} — leaving in queue for retry`);
    }
  }
  if (learned.length) markProcessed(learned);

  // 4. REFRESH patterns if enough new data landed
  if (learned.length >= PATTERN_REFRESH_AT) {
    refreshPatterns();
  } else {
    console.log(
      `  • ${learned.length} learned this cycle — patterns refresh threshold is ${PATTERN_REFRESH_AT}, not regenerating yet`
    );
  }

  console.log(`[${ts()}] cycle done — ${learned.length} new outliers analyzed\n`);
}

async function runLoop(): Promise<void> {
  console.log(`watch loop starting — every ${INTERVAL_MIN} min`);
  console.log(`  competitors: ${join(ROOT, "competitors.json")}`);
  console.log(`  outlier rule: views > 5x handle's median`);
  console.log(`  pattern refresh: every ${PATTERN_REFRESH_AT} new outliers learned`);
  console.log(`  ctrl+c to stop\n`);

  const tick = async () => {
    try {
      await runOnce();
    } catch (e: any) {
      console.error(`[${ts()}] cycle error:`, e?.message || e);
    }
  };

  await tick();
  setInterval(tick, INTERVAL_MIN * 60 * 1000);
}

async function main() {
  const cmd = process.argv[2] || "once";
  if (cmd === "once") {
    await runOnce();
  } else if (cmd === "loop") {
    await runLoop();
  } else {
    console.error(`unknown subcommand: ${cmd}\nuse: once | loop`);
    process.exit(1);
  }
}

main().catch((e) => {
  console.error("ERROR:", e?.message || e);
  process.exit(1);
});
