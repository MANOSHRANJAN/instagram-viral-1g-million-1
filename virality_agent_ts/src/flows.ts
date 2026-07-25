// IG flows — Tool Router lets the agent call Firecrawl/Exa/IG itself.
// We give it a clear job, it picks the tools, returns structured JSON.
import { runAgent, extractJson } from "./agent.js";
import { ANALYZER_SYSTEM, CRITIC_SYSTEM, WRITER_SYSTEM, analyzerPrompt, criticPrompt, writerPrompt } from "./prompts.js";
import { loadStyle, styleAsPromptBlock } from "./style.js";
import type { Config } from "./config.js";

export interface ReelLite {
  url: string;
  views?: number;
  likes?: number;
  comments?: number;
  caption?: string;
}

export interface ProfileScroll {
  handle: string;
  bio: string;
  followerCount: number | null;
  reels: ReelLite[];
  error?: string;
}

const SCROLL_SYS = `You are an Instagram research agent. You have access to Firecrawl
through the composio MCP server (look for FIRECRAWL_EXTRACT or similar). Your job is to
call it on a public Instagram profile/reels URL and return STRUCTURED DATA only — no prose.
Always end your response with one valid JSON object inside a fenced \`\`\`json block.`;

export async function scrollProfile(
  cfg: Config,
  handle: string,
  topK: number
): Promise<ProfileScroll> {
  const cleaned = handle.replace(/^@/, "").trim();
  const profileUrl = `https://www.instagram.com/${cleaned}/`;
  const reelsUrl = `https://www.instagram.com/${cleaned}/reels/`;

  const prompt = `Use Firecrawl (via the composio tool router) to scrape these two Instagram URLs:
- ${profileUrl}
- ${reelsUrl}

For each one, call FIRECRAWL_EXTRACT (or whichever Firecrawl tool the router exposes) with a JSON
schema that captures: bio, follower_count, and a list of reels with {url, views, likes, comments, caption}.
Pull the top ${topK} reels by engagement.

Return a single JSON object with this shape:
{
  "handle": "${cleaned}",
  "bio": "...",
  "follower_count": 12345,
  "reels": [
    {"url": "https://www.instagram.com/reel/...", "views": 0, "likes": 0, "comments": 0, "caption": "..."}
  ]
}

If a tool fails, set "error" and return whatever partial data you have.`;

  const text = await runAgent(cfg, prompt, { systemPrompt: SCROLL_SYS, maxTurns: 8 });
  const j = extractJson(text);
  return {
    handle: j.handle || cleaned,
    bio: j.bio || "",
    followerCount: j.follower_count ?? null,
    reels: Array.isArray(j.reels) ? j.reels.slice(0, topK) : [],
    error: j.error,
  };
}

export interface VideoFacts {
  url: string;
  author: string;
  caption: string;
  transcript: string;
  views: number | null;
  likes: number | null;
  comments: number | null;
  duration: number | null;
  error?: string;
}

const FETCH_SYS = `You are a reel-fetcher. You have MCP tools through the composio server. ONE-PASS RULE:
1. Try ONE Firecrawl scrape on the URL. Tools that return 403/unsupported on Instagram, MOVE ON.
2. If Firecrawl fails, try ONE alternative tool (apify, brightdata, exa, supadata).
3. After at MOST 3 distinct tool attempts, STOP and return whatever you got — even partial.
NEVER retry the same tool more than once. NEVER call browser_tool more than once.
ALWAYS finish your turn by emitting the JSON, even if every tool failed.`;

export async function fetchReel(cfg: Config, url: string): Promise<VideoFacts> {
  const prompt = `Extract this Instagram reel through the composio MCP server:
${url}

Pull author handle, caption, spoken/on-screen transcript, views, likes, comments, duration.

ONE-PASS PROTOCOL (do NOT loop):
- Attempt 1: Firecrawl (will likely fail on IG with 403, that's fine)
- Attempt 2: try ONE other tool (apify / brightdata / exa / supadata / browser_tool)
- Attempt 3: if anything still fails, STOP — return what you have.

Return ONE JSON object even if data is partial:
{
  "url": "${url}",
  "author": "...",
  "caption": "...",
  "transcript": "...",
  "views": 0,
  "likes": 0,
  "comments": 0,
  "duration_seconds": 0,
  "error": "(only if every tool failed — list what you tried)"
}`;
  const text = await runAgent(cfg, prompt, { systemPrompt: FETCH_SYS, maxTurns: 6 });
  const j = extractJson(text);
  return {
    url: j.url || url,
    author: String(j.author || ""),
    caption: String(j.caption || ""),
    transcript: String(j.transcript || ""),
    views: numOrNull(j.views),
    likes: numOrNull(j.likes),
    comments: numOrNull(j.comments),
    duration: numOrNull(j.duration_seconds),
    error: j.error,
  };
}

export async function analyzeReel(cfg: Config, facts: VideoFacts): Promise<any> {
  const style = loadStyle();
  const prompt = analyzerPrompt({
    avatar: style.avatar || style.targetAudience,
    url: facts.url,
    author: facts.author,
    views: facts.views,
    likes: facts.likes,
    comments: facts.comments,
    duration: facts.duration,
    caption: facts.caption,
    transcript: facts.transcript,
  });
  const text = await runAgent(cfg, prompt, { systemPrompt: ANALYZER_SYSTEM, maxTurns: 2 });
  return extractJson(text);
}

export async function generateScript(
  cfg: Config,
  pairs: Array<{ facts: VideoFacts; analysis: any }>,
  topic: string | null
): Promise<any> {
  const style = loadStyle();
  const inspiration = pairs
    .slice(0, 5)
    .map((p) =>
      JSON.stringify(
        {
          url: p.facts.url,
          topic: p.analysis?.topic,
          hook: p.analysis?.hook?.first_3_seconds,
          hook_type: p.analysis?.hook?.hook_type,
          score: p.analysis?.virality_score?.score_0_100,
          drift: p.analysis?.audience_match?.topic_drift_warning,
        },
        null,
        2
      )
    )
    .join("\n\n");
  const text = await runAgent(
    cfg,
    writerPrompt({ styleBlock: styleAsPromptBlock(style), inspiration, topic }),
    { systemPrompt: WRITER_SYSTEM, maxTurns: 2 }
  );
  return extractJson(text);
}

export async function critiqueScript(
  cfg: Config,
  script: { hook: string; script: string; cta: string }
): Promise<any> {
  const style = loadStyle();
  const text = await runAgent(
    cfg,
    criticPrompt({
      avatar: style.avatar || style.targetAudience,
      hook: script.hook,
      script: script.script,
      cta: script.cta,
    }),
    { systemPrompt: CRITIC_SYSTEM, maxTurns: 2 }
  );
  return extractJson(text);
}

function numOrNull(v: any): number | null {
  if (v === null || v === undefined || v === "") return null;
  if (typeof v === "number") return v;
  const s = String(v).toLowerCase().replace(/,/g, "").trim();
  const m = s.match(/([\d.]+)\s*([kmb]?)/);
  if (!m) return null;
  const mul: Record<string, number> = { k: 1_000, m: 1_000_000, b: 1_000_000_000 };
  return Math.round(parseFloat(m[1]) * (mul[m[2]] || 1));
}
