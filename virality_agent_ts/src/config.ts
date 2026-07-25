// Loads keys from ../composio.env and ../anthropic.env
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const WORKSPACE = join(__dirname, "..", "..");

function parseDotEnv(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const raw of text.split("\n")) {
    const m = raw.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$/);
    if (m) out[m[1]] = m[2].replace(/^['"]|['"]$/g, "");
  }
  return out;
}

function parseAnthropicEnv(text: string): Record<string, string> {
  const out = parseDotEnv(text);
  if (text.includes("curl")) {
    const k = text.match(/x-api-key:\s*([^\s'"]+)/);
    if (k && !out.ANTHROPIC_API_KEY) out.ANTHROPIC_API_KEY = k[1];
    const u = text.match(/https?:\/\/[^\s'"/]+(?:\/[^\s'"]*)?/);
    if (u && !out.ANTHROPIC_BASE_URL) {
      out.ANTHROPIC_BASE_URL = u[0].replace(/\/$/, "").replace(/\/v1\/messages.*$/, "");
    }
    const m = text.match(/"model"\s*:\s*"([^"]+)"/);
    if (m && !out.CLAUDE_MODEL) out.CLAUDE_MODEL = m[1];
  }
  return out;
}

function readIfExists(p: string): string {
  return existsSync(p) ? readFileSync(p, "utf-8") : "";
}

export interface Config {
  composioApiKey: string;
  anthropicApiKey: string;
  anthropicBaseUrl: string;
  claudeModel: string;
  userId: string;
  igCookiesFile: string;
}

export function loadConfig(): Config {
  const composioRaw = readIfExists(join(WORKSPACE, "composio.env"));
  const composio = parseDotEnv(composioRaw);
  const anthropic = parseAnthropicEnv(readIfExists(join(WORKSPACE, "anthropic.env")));

  const composioApiKey =
    composio.COMPOSIO_API_KEY ||
    composio.apikey ||
    composio.APIKEY ||
    process.env.COMPOSIO_API_KEY ||
    "";

  if (!composioApiKey) {
    throw new Error(
      "COMPOSIO_API_KEY missing. Put it in composio.env (apikey=...) at workspace root."
    );
  }

  // Find IG cookies file at workspace root
  let cookies = process.env.IG_COOKIES_FILE || "";
  if (!cookies) {
    for (const name of ["instagram_cookies.txt", "ig_cookies.txt", "cookies.txt"]) {
      const p = join(WORKSPACE, name);
      if (existsSync(p)) {
        cookies = p;
        break;
      }
    }
  }

  return {
    composioApiKey,
    anthropicApiKey:
      anthropic.ANTHROPIC_API_KEY || process.env.ANTHROPIC_API_KEY || "",
    anthropicBaseUrl:
      anthropic.ANTHROPIC_BASE_URL || process.env.ANTHROPIC_BASE_URL || "",
    claudeModel:
      anthropic.CLAUDE_MODEL || process.env.CLAUDE_MODEL || "claude-opus-4-7",
    userId: process.env.COMPOSIO_USER_ID || "virality_agent",
    igCookiesFile: cookies,
  };
}
