// `learn <url> <url> ...` — download each reel via yt-dlp, run the Bible-grounded
// vision analyzer on each, save the analyses to learned/<timestamp>.json.
//
// Falls back to caption-only analysis if yt-dlp can't download (no IG cookies, etc).
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, basename, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import Anthropic from "@anthropic-ai/sdk";
import { loadConfig } from "./config.js";
import { ANALYZER_SYSTEM, analyzerPrompt } from "./prompts.js";
import { loadStyle } from "./style.js";
import { extractJson } from "./agent.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const WORKSPACE = join(__dirname, "..", "..");
const LEARNED_DIR = join(__dirname, "..", "learned");

interface LearnedReel {
  url: string;
  source: "url-yt-dlp" | "local-file";
  duration_seconds: number;
  hook_frame_count: number;
  scene_frame_count: number;
  transcript: string;
  analysis: any;
  analyzed_at: string;
}

function igCookiesFile(): string | null {
  for (const name of ["instagram_cookies.txt", "ig_cookies.txt", "cookies.txt"]) {
    const p = join(WORKSPACE, name);
    if (existsSync(p)) return p;
  }
  return null;
}

function ffprobeDuration(path: string): number {
  const r = spawnSync("ffprobe", [
    "-v", "error",
    "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1",
    path,
  ]);
  return parseFloat(r.stdout.toString().trim() || "0");
}

function downloadVideo(url: string, outDir: string): { path: string | null; error?: string } {
  const out = join(outDir, "reel.mp4");
  const args = [
    "--quiet", "--no-warnings",
    "-f", "mp4/best[ext=mp4]/best",
    "-o", out,
  ];
  const cookies = igCookiesFile();
  if (cookies) args.push("--cookies", cookies);
  args.push(url);
  const r = spawnSync("yt-dlp", args, { timeout: 300_000 });
  if (r.status !== 0) {
    const stderr = (r.stderr || Buffer.from("")).toString().slice(0, 400);
    return { path: null, error: `yt-dlp failed: ${stderr}` };
  }
  if (!existsSync(out) || statSync(out).size < 1024) {
    return { path: null, error: "downloaded file missing or too small" };
  }
  return { path: out };
}

function extractFrames(videoPath: string): { hook: string[]; scene: string[]; audio: string; duration: number; workdir: string } {
  const workdir = mkdtempSync(join(tmpdir(), "virality_learn_"));
  const duration = ffprobeDuration(videoPath);
  const hookDir = join(workdir, "hook");
  const sceneDir = join(workdir, "scene");
  mkdirSync(hookDir, { recursive: true });
  mkdirSync(sceneDir, { recursive: true });

  spawnSync("ffmpeg", [
    "-y", "-loglevel", "error",
    "-t", "10",
    "-i", videoPath,
    "-vf", "fps=2,scale=480:-1",
    join(hookDir, "hook_%03d.jpg"),
  ]);
  spawnSync("ffmpeg", [
    "-y", "-loglevel", "error",
    "-i", videoPath,
    "-vf", "select='gt(scene,0.30)',scale=480:-1",
    "-vsync", "vfr",
    join(sceneDir, "scene_%03d.jpg"),
  ]);
  const audio = join(workdir, "audio.mp3");
  spawnSync("ffmpeg", [
    "-y", "-loglevel", "error",
    "-i", videoPath,
    "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k",
    audio,
  ]);

  const hook = readdirSync(hookDir).filter((f) => f.endsWith(".jpg")).sort().map((f) => join(hookDir, f));
  const scene = readdirSync(sceneDir).filter((f) => f.endsWith(".jpg")).sort().map((f) => join(sceneDir, f));
  return { hook, scene, audio, duration, workdir };
}

async function transcribeWithGroq(audioPath: string): Promise<string> {
  const groqKey = process.env.GROQ_API_KEY;
  if (!groqKey || !existsSync(audioPath)) return "";
  try {
    const audio = readFileSync(audioPath);
    const fd = new FormData();
    fd.set("file", new Blob([audio], { type: "audio/mpeg" }), basename(audioPath));
    fd.set("model", "whisper-large-v3");
    fd.set("response_format", "json");
    const r = await fetch("https://api.groq.com/openai/v1/audio/transcriptions", {
      method: "POST",
      headers: { Authorization: `Bearer ${groqKey}` },
      body: fd,
    });
    if (!r.ok) return "";
    const j = (await r.json()) as { text?: string };
    return j.text || "";
  } catch {
    return "";
  }
}

async function analyzeOne(url: string): Promise<LearnedReel | null> {
  const cfg = loadConfig();
  if (!cfg.anthropicApiKey) {
    console.error("ANTHROPIC_API_KEY missing");
    return null;
  }

  const tmp = mkdtempSync(join(tmpdir(), "virality_dl_"));
  console.log(`  → downloading ${url}`);
  const dl = downloadVideo(url, tmp);
  if (!dl.path) {
    console.log(`  ⚠ download failed: ${dl.error}`);
    console.log(`  (analysis without frames is still possible later — saving placeholder)`);
    return null;
  }
  return await analyzeFile(dl.path, url, "url-yt-dlp");
}

async function analyzeLocal(path: string): Promise<LearnedReel | null> {
  const cfg = loadConfig();
  if (!cfg.anthropicApiKey) {
    console.error("ANTHROPIC_API_KEY missing");
    return null;
  }
  return await analyzeFile(path, `file://${path}`, "local-file");
}

async function analyzeFile(
  videoPath: string,
  url: string,
  source: "url-yt-dlp" | "local-file"
): Promise<LearnedReel | null> {
  const cfg = loadConfig();
  console.log(`  → extracting frames + audio`);
  const x = extractFrames(videoPath);
  console.log(`     duration ${x.duration.toFixed(1)}s · ${x.hook.length} hook · ${x.scene.length} scene`);

  console.log(`  → transcribing (groq whisper if GROQ_API_KEY set)`);
  const transcript = await transcribeWithGroq(x.audio);
  if (transcript) console.log(`     ${transcript.slice(0, 100)}...`);
  else console.log(`     (no transcript — vision-only)`);

  console.log(`  → calling Claude with frames`);
  const anthropic = new Anthropic({
    apiKey: cfg.anthropicApiKey,
    baseURL: cfg.anthropicBaseUrl || undefined,
  });
  const style = loadStyle();
  const promptText = analyzerPrompt({
    avatar: style.avatar || style.targetAudience,
    url,
    author: "(unknown)",
    views: null,
    likes: null,
    comments: null,
    duration: Math.round(x.duration),
    caption: "",
    transcript,
  });

  const allFrames = [...x.hook, ...x.scene].slice(0, 12);
  const content: any[] = [{ type: "text", text: promptText }];
  for (const fp of allFrames) {
    try {
      const b64 = readFileSync(fp).toString("base64");
      content.push({
        type: "image",
        source: { type: "base64", media_type: "image/jpeg", data: b64 },
      });
    } catch { /* skip */ }
  }

  const msg = await anthropic.messages.create({
    model: cfg.claudeModel,
    max_tokens: 4000,
    system: ANALYZER_SYSTEM,
    messages: [{ role: "user", content }],
  });
  const text = msg.content
    .filter((b: any) => b.type === "text")
    .map((b: any) => b.text)
    .join("\n");
  const analysis = extractJson(text);

  return {
    url,
    source,
    duration_seconds: Math.round(x.duration),
    hook_frame_count: x.hook.length,
    scene_frame_count: x.scene.length,
    transcript,
    analysis,
    analyzed_at: new Date().toISOString(),
  };
}

async function main() {
  const args = process.argv.slice(2);
  const DEFAULT_FOLDER = join(process.env.HOME || "", "Downloads", "JS RAM");
  let videoSources: { source: "url-yt-dlp" | "local-file"; url?: string; path?: string }[] = [];

  if (!args.length || args[0] === "--folder" || args[0].startsWith("/") || args[0].startsWith("~")) {
    // FOLDER MODE — scan a directory for mp4s, default to ~/Downloads/JS RAM
    let folder = DEFAULT_FOLDER;
    if (args.length && args[0] !== "--folder") folder = args[0].replace("~", process.env.HOME || "");
    else if (args.length && args[0] === "--folder" && args[1]) folder = args[1].replace("~", process.env.HOME || "");

    if (!existsSync(folder)) {
      console.error(`folder not found: ${folder}`);
      process.exit(1);
    }
    const mp4s = readdirSync(folder)
      .filter((f) => f.toLowerCase().endsWith(".mp4"))
      .map((f) => join(folder, f));
    if (!mp4s.length) {
      console.error(`no .mp4 files in ${folder}`);
      process.exit(1);
    }
    console.log(`found ${mp4s.length} mp4 files in ${folder}`);
    videoSources = mp4s.map((p) => ({ source: "local-file", path: p }));
  } else {
    // URL MODE — yt-dlp each
    videoSources = args.map((url) => ({ source: "url-yt-dlp", url }));
  }

  mkdirSync(LEARNED_DIR, { recursive: true });

  const results: LearnedReel[] = [];
  for (let i = 0; i < videoSources.length; i++) {
    const v = videoSources[i];
    console.log(`\n[${i + 1}/${videoSources.length}] ${v.url || basename(v.path!)}`);
    try {
      const r = v.source === "url-yt-dlp"
        ? await analyzeOne(v.url!)
        : await analyzeLocal(v.path!);
      if (r) results.push(r);
    } catch (e: any) {
      console.log(`  ⚠ analyze error: ${e?.message || e}`);
    }
  }

  if (!results.length) {
    console.log("\nno reels analyzed.");
    process.exit(1);
  }

  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const outPath = join(LEARNED_DIR, `batch_${stamp}.json`);
  writeFileSync(outPath, JSON.stringify(results, null, 2));
  console.log(`\nsaved ${results.length} analyses → ${outPath}`);

  const allPath = join(LEARNED_DIR, "all.json");
  let all: LearnedReel[] = [];
  if (existsSync(allPath)) {
    try { all = JSON.parse(readFileSync(allPath, "utf-8")); } catch { all = []; }
  }
  all.push(...results);
  writeFileSync(allPath, JSON.stringify(all, null, 2));
  console.log(`appended → ${allPath} (total: ${all.length})`);
}

main().catch((e) => {
  console.error("ERROR:", e?.message || e);
  process.exit(1);
});
