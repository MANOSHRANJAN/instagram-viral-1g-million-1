// IG scout — Playwright-based scraper using a saved auth_state.json.
// First run: opens visible Chrome, you log in like a human, exit.
// Subsequent runs: headless, reuses the session.
//
// Usage:
//   npx tsx src/scout.ts login                  → opens browser, you log in, saves auth state
//   npx tsx src/scout.ts profile <handle>       → pulls last 12 reels for one creator
//   npx tsx src/scout.ts all                    → loops through competitors.json
import { chromium, type BrowserContext } from "playwright";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const AUTH_DIR = join(ROOT, "auth");
const AUTH_STATE = join(AUTH_DIR, "instagram.json");
const COMPETITORS_PATH = join(ROOT, "competitors.json");
const SCOUT_DIR = join(ROOT, "scout");

export interface ScoutedReel {
  url: string;
  shortcode: string;
  views: number | null;
  likes: number | null;
  comments: number | null;
  caption: string;
  posted_iso?: string;
  duration?: number;
  scouted_at: string;
}

export interface ScoutedProfile {
  handle: string;
  scouted_at: string;
  followers: number | null;
  reels: ScoutedReel[];
}

function ensureDirs() {
  mkdirSync(AUTH_DIR, { recursive: true });
  mkdirSync(SCOUT_DIR, { recursive: true });
}

async function newContext(headless: boolean): Promise<BrowserContext> {
  ensureDirs();
  const browser = await chromium.launch({
    headless,
    args: ["--disable-blink-features=AutomationControlled"],
  });
  const ctxOpts: any = {
    viewport: { width: 1280, height: 900 },
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 " +
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    locale: "en-US",
  };
  if (existsSync(AUTH_STATE)) ctxOpts.storageState = AUTH_STATE;
  return await browser.newContext(ctxOpts);
}

export async function login(): Promise<void> {
  ensureDirs();
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
  });
  const page = await context.newPage();
  console.log("→ opening instagram.com — log in like a human (any account, ideally NOT your main one)");
  console.log("  • Tick 'save your login info' when IG offers");
  console.log("  • Once you see your home feed, come back here and press ENTER");
  await page.goto("https://www.instagram.com/", { waitUntil: "domcontentloaded" });

  await new Promise<void>((resolve) => {
    process.stdin.resume();
    process.stdin.once("data", () => resolve());
  });

  await context.storageState({ path: AUTH_STATE });
  console.log(`✓ saved session → ${AUTH_STATE}`);
  await browser.close();
  process.exit(0);
}

function parseCount(text: string): number | null {
  if (!text) return null;
  const s = text.toLowerCase().replace(/,/g, "").trim();
  const m = s.match(/([\d.]+)\s*([kmb]?)/);
  if (!m) return null;
  const mul: Record<string, number> = { k: 1_000, m: 1_000_000, b: 1_000_000_000 };
  return Math.round(parseFloat(m[1]) * (mul[m[2]] || 1));
}

export async function scoutProfile(handle: string, max: number = 12): Promise<ScoutedProfile> {
  if (!existsSync(AUTH_STATE)) {
    throw new Error(`no auth state — run \`npm run scout:login\` first`);
  }
  const cleaned = handle.replace(/^@/, "").trim();
  const context = await newContext(true);
  const page = await context.newPage();

  console.log(`  → loading @${cleaned}`);
  await page.goto(`https://www.instagram.com/${cleaned}/`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500 + Math.random() * 1500);

  // followers (best-effort)
  let followers: number | null = null;
  try {
    const txt = await page.locator('a[href$="/followers/"]').first().innerText({ timeout: 4000 });
    followers = parseCount(txt);
  } catch { /* ignore */ }

  // collect reel shortcodes by walking the page DOM
  console.log(`  → going to /reels/`);
  await page.goto(`https://www.instagram.com/${cleaned}/reels/`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500 + Math.random() * 1500);

  for (let i = 0; i < 4; i++) {
    await page.mouse.wheel(0, 1500);
    await page.waitForTimeout(900 + Math.random() * 600);
  }

  const reelLinks: string[] = await page.$$eval("a[href*='/reel/']", (els) =>
    Array.from(new Set(els.map((e: any) => e.href).filter((h: string) => h.includes("/reel/"))))
  );
  const shortcodes = Array.from(
    new Set(reelLinks.map((u) => (u.match(/\/reel\/([^/?]+)/) || [])[1]).filter(Boolean))
  ).slice(0, max);

  console.log(`  → found ${shortcodes.length} reel shortcodes`);

  const reels: ScoutedReel[] = [];
  for (const code of shortcodes) {
    const url = `https://www.instagram.com/reel/${code}/`;
    try {
      await page.goto(url, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1500 + Math.random() * 1200);

      // Grab visible counts + caption from the page DOM (selectors are fragile, fall back gracefully)
      const data = await page.evaluate(() => {
        const text = document.body.innerText;
        const captionMatch = text.match(/[\s\S]{0,400}/);
        const viewsM = text.match(/([\d.,]+\s*[KMB]?)\s+view/i);
        const likesM = text.match(/([\d.,]+\s*[KMB]?)\s+like/i);
        const commentsM = text.match(/([\d.,]+)\s+comment/i);
        return {
          rawText: text.slice(0, 1200),
          views: viewsM?.[1] || null,
          likes: likesM?.[1] || null,
          comments: commentsM?.[1] || null,
        };
      });

      reels.push({
        url,
        shortcode: code,
        views: parseCount(data.views || ""),
        likes: parseCount(data.likes || ""),
        comments: parseCount(data.comments || ""),
        caption: (data.rawText || "").slice(0, 600),
        scouted_at: new Date().toISOString(),
      });
    } catch (e: any) {
      console.log(`    ⚠ ${code}: ${e?.message?.slice(0, 80) || e}`);
    }
  }

  await context.close();

  return {
    handle: cleaned,
    scouted_at: new Date().toISOString(),
    followers,
    reels,
  };
}

export function loadHistory(handle: string): ScoutedProfile[] {
  const p = join(SCOUT_DIR, `${handle}.json`);
  if (!existsSync(p)) return [];
  try {
    return JSON.parse(readFileSync(p, "utf-8"));
  } catch {
    return [];
  }
}

export function appendHistory(handle: string, snapshot: ScoutedProfile): void {
  ensureDirs();
  const history = loadHistory(handle);
  history.push(snapshot);
  writeFileSync(join(SCOUT_DIR, `${handle}.json`), JSON.stringify(history, null, 2));
}

export function loadCompetitors(): string[] {
  if (!existsSync(COMPETITORS_PATH)) {
    const seed = [
      "thevarunmayya",
      "rowancheung",
      "therundownai",
      "vaibhavsisinty",
      "createcontent.club",
    ];
    writeFileSync(COMPETITORS_PATH, JSON.stringify(seed, null, 2));
    console.log(`(seeded ${COMPETITORS_PATH} — edit to change competitor list)`);
    return seed;
  }
  return JSON.parse(readFileSync(COMPETITORS_PATH, "utf-8"));
}

async function main() {
  const cmd = process.argv[2] || "all";
  if (cmd === "login") {
    await login();
    return;
  }
  if (cmd === "profile") {
    const handle = process.argv[3];
    if (!handle) {
      console.error("usage: npx tsx src/scout.ts profile <handle>");
      process.exit(1);
    }
    console.log(`scouting @${handle}`);
    const snap = await scoutProfile(handle);
    appendHistory(snap.handle, snap);
    console.log(JSON.stringify(snap, null, 2));
    return;
  }
  if (cmd === "all") {
    const list = loadCompetitors();
    console.log(`scouting ${list.length} creators`);
    for (const h of list) {
      try {
        const snap = await scoutProfile(h);
        appendHistory(snap.handle, snap);
        console.log(`✓ ${h} — ${snap.reels.length} reels`);
      } catch (e: any) {
        console.log(`✗ ${h} — ${e?.message?.slice(0, 100)}`);
      }
    }
    return;
  }
  console.error(`unknown subcommand: ${cmd}\nuse: login | profile <handle> | all`);
  process.exit(1);
}

if (process.argv[1] && process.argv[1].endsWith("scout.ts")) {
  main().catch((e) => {
    console.error("ERROR:", e?.message || e);
    process.exit(1);
  });
}
