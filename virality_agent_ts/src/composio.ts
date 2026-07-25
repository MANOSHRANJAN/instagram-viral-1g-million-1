// Composio Tool Router session — one session unlocks Firecrawl, Exa, IG, etc.
// without per-toolkit auth dance.
import { Composio } from "@composio/core";
import { ClaudeAgentSDKProvider } from "@composio/claude-agent-sdk";
import type { Config } from "./config.js";

let _session: any = null;
let _composio: any = null;

export async function getToolRouterSession(cfg: Config) {
  if (_session) return _session;
  _composio = new Composio({
    apiKey: cfg.composioApiKey,
    provider: new ClaudeAgentSDKProvider(),
  });
  _session = await _composio.create(cfg.userId);
  return _session;
}

export async function getRouterTools(cfg: Config) {
  const session = await getToolRouterSession(cfg);
  return await session.tools();
}

export function rawComposio(cfg: Config) {
  if (!_composio) {
    _composio = new Composio({
      apiKey: cfg.composioApiKey,
      provider: new ClaudeAgentSDKProvider(),
    });
  }
  return _composio;
}
