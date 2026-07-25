// Analyze a LOCAL video file end-to-end against the Algorithm Bible.
// Skips yt-dlp entirely — ffmpeg + Claude vision only.
// Run: npx tsx src/analyze_local.ts /path/to/video.mp4
import { existsSync, mkdtempSync, readFileSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, basename } from "node:path";
import { spawnSync } from "node:child_process";
import Anthropic from "@anthropic-ai/sdk";
import { loadConfig } from "./config.js";
import { ANALYZER_SYSTEM, analyzerPrompt } from "./prompts.js";
import { loadStyle } from "./style.js";
import { extractJson } from "./agent.js";

interface ExtractResult {
  duration: number;
  hookFrames: string[];
  sceneFrames: string[];
  audioPath: string;
  workdir: string;
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

function extractFrames(videoPath: string): ExtractResult {
  const workdir = mkdtempSync(join(tmpdir(), "virality_local_"));
  const duration = ffprobeDuration(videoPath);
  const hookDir = join(workdir, "hook");
  const sceneDir = join(workdir, "scene");
  spawnSync("mkdir", ["-p", hookDir, sceneDir]);

  // 0-10s hook microscope @ 2fps
  spawnSync("ffmpeg", [
    "-y", "-loglevel", "error",
    "-t", "10",
    "-i", videoPath,
    "-vf", "fps=2,scale=480:-1",
    join(hookDir, "hook_%03d.jpg"),
  ]);

  // Scene-change frames
  spawnSync("ffmpeg", [
    "-y", "-loglevel", "error",
    "-i", videoPath,
    "-vf", "select='gt(scene,0.30)',scale=480:-1",
    "-vsync", "vfr",
    join(sceneDir, "scene_%03d.jpg"),
  ]);

  // Audio for transcription
  const audioPath = join(workdir, "audio.mp3");
  spawnSync("ffmpeg", [
    "-y", "-loglevel", "error",
    "-i", videoPath,
    "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k",
    audioPath,
  ]);

  const hookFrames = readdirSync(hookDir).filter((f) => f.endsWith(".jpg")).sort().map((f) => join(hookDir, f));
  const sceneFrames = readdirSync(sceneDir).filter((f) => f.endsWith(".jpg")).sort().map((f) => join(sceneDir, f));
  return { duration, hookFrames, sceneFrames, audioPath, workdir };
}

function frameToB64(path: string): string {
  return readFileSync(path).toString("base64");
}

async function transcribeWithGroq(audioPath: string): Promise<string> {
  const groqKey = process.env.GROQ_API_KEY;
  if (!groqKey) return "";
  try {
    const FormData = (await import("node:buffer")).Blob ? globalThis.FormData : null;
    if (!FormData) return "";
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

async function main() {
  const videoPath = process.argv[2];
  if (!videoPath) {
    console.error("usage: npx tsx src/analyze_local.ts <video-path>");
    process.exit(1);
  }
  if (!existsSync(videoPath)) {
    console.error(`not found: ${videoPath}`);
    process.exit(1);
  }
  console.log(`→ analyzing ${basename(videoPath)}`);

  const cfg = loadConfig();
  if (!cfg.anthropicApiKey) {
    console.error("ANTHROPIC_API_KEY missing — add it to anthropic.env");
    process.exit(1);
  }

  console.log("  → extracting frames + audio");
  const r = extractFrames(videoPath);
  console.log(`  duration: ${r.duration.toFixed(1)}s | hook frames: ${r.hookFrames.length} | scene frames: ${r.sceneFrames.length}`);

  console.log("  → transcribing audio (groq whisper if GROQ_API_KEY set, else skip)");
  const transcript = await transcribeWithGroq(r.audioPath);
  if (transcript) {
    console.log(`  transcript: ${transcript.slice(0, 120)}...`);
  } else {
    console.log("  (no transcript — vision-only analysis)");
  }

  console.log("  → calling Claude with frames");
  const anthropic = new Anthropic({
    apiKey: cfg.anthropicApiKey,
    baseURL: cfg.anthropicBaseUrl || undefined,
  });

  const style = loadStyle();
  const promptText = analyzerPrompt({
    avatar: style.avatar || style.targetAudience,
    url: `file://${videoPath}`,
    author: "(local file)",
    views: null,
    likes: null,
    comments: null,
    duration: Math.round(r.duration),
    caption: "",
    transcript,
  });

  const allFrames = [...r.hookFrames, ...r.sceneFrames].slice(0, 12);
  const content: any[] = [{ type: "text", text: promptText }];
  for (const fp of allFrames) {
    try {
      const b64 = frameToB64(fp);
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
  const text = msg.content.filter((b: any) => b.type === "text").map((b: any) => b.text).join("\n");
  const j = extractJson(text);

  console.log("\n=== ANALYSIS ===");
  console.log(JSON.stringify(j, null, 2));
}

main().catch((e) => {
  console.error("ERROR:", e?.message || e);
  process.exit(1);
});
