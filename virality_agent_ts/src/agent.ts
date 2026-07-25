// Run a Claude Agent SDK query against the local Anthropic proxy,
// with the Composio Tool Router exposed as the `composio` MCP server.
import { createSdkMcpServer, query } from "@anthropic-ai/claude-agent-sdk";
import { getRouterTools } from "./composio.js";
import type { Config } from "./config.js";

export interface AgentRunOptions {
  systemPrompt?: string;
  maxTurns?: number;
}

export async function runAgent(
  cfg: Config,
  prompt: string,
  opts: AgentRunOptions = {}
): Promise<string> {
  if (cfg.anthropicBaseUrl) {
    process.env.ANTHROPIC_BASE_URL = cfg.anthropicBaseUrl;
  }
  if (cfg.anthropicApiKey) {
    process.env.ANTHROPIC_API_KEY = cfg.anthropicApiKey;
  }

  const tools = await getRouterTools(cfg);
  const composioServer = createSdkMcpServer({
    name: "composio",
    version: "1.0.0",
    tools,
  });

  const out: string[] = [];
  for await (const content of query({
    prompt,
    options: {
      mcpServers: { composio: composioServer },
      permissionMode: "bypassPermissions",
      model: cfg.claudeModel,
      ...(opts.systemPrompt ? { systemPrompt: opts.systemPrompt } : {}),
      ...(opts.maxTurns ? { maxTurns: opts.maxTurns } : {}),
    },
  })) {
    if (content.type === "assistant") {
      const msg: any = content.message;
      const blocks = Array.isArray(msg?.content) ? msg.content : [];
      for (const b of blocks) {
        if (b?.type === "text" && typeof b.text === "string") out.push(b.text);
      }
    }
  }
  return out.join("\n");
}

export function extractJson(text: string): any {
  let t = text.trim();
  if (t.startsWith("```")) {
    t = t.replace(/^```(?:json)?/i, "").replace(/```$/, "").trim();
  }
  const start = t.indexOf("{");
  const end = t.lastIndexOf("}");
  if (start === -1 || end === -1) return { _raw: text };
  try {
    return JSON.parse(t.slice(start, end + 1));
  } catch {
    return { _raw: text };
  }
}
