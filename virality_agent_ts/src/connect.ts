// One-off: generate a Composio connect link for a toolkit (default: firecrawl).
// Tries the auth-config-then-initiate path the dashboard uses.
// Run with: npx tsx src/connect.ts firecrawl
import { Composio } from "@composio/core";
import { loadConfig } from "./config.js";

async function main() {
  const toolkit = (process.argv[2] || "firecrawl").toLowerCase();
  const cfg = loadConfig();
  const composio: any = new Composio({ apiKey: cfg.composioApiKey });

  // Step 1: find or create an auth config for this toolkit
  let authConfigId: string | undefined;
  try {
    const list = await composio.authConfigs.list({ toolkit });
    const items = list?.items || list?.data || [];
    if (items.length) {
      authConfigId = items[0].id || items[0].nanoid;
      console.log(`(reusing existing auth config: ${authConfigId})`);
    }
  } catch (e: any) {
    console.log(`(authConfigs.list error: ${e?.message})`);
  }

  if (!authConfigId) {
    try {
      const created = await composio.authConfigs.create(toolkit, {
        type: "use_composio_managed_auth",
      });
      authConfigId = created?.id || created?.nanoid;
      console.log(`(created managed auth config: ${authConfigId})`);
    } catch (e: any) {
      console.log(`(authConfigs.create error: ${e?.message})`);
    }
  }

  if (!authConfigId) {
    console.error(
      `\nCould not get an auth config id for ${toolkit}. ` +
        `Composio probably doesn't have managed auth for this toolkit on your tier — ` +
        `you'll need to create one in the dashboard:\n` +
        `  https://platform.composio.dev/marketplace/${toolkit}\n`
    );
    process.exit(2);
  }

  // Step 2: initiate a connection using that auth config
  let conn: any;
  try {
    conn = await composio.connectedAccounts.initiate(cfg.userId, authConfigId);
  } catch (e1: any) {
    try {
      conn = await composio.connectedAccounts.initiate({
        userId: cfg.userId,
        authConfigId,
      });
    } catch (e2: any) {
      console.error("initiate (positional):", e1?.message);
      console.error("initiate (object):    ", e2?.message);
      throw e2;
    }
  }

  const url =
    conn?.redirectUrl ||
    conn?.redirect_url ||
    conn?.connectionStatus?.redirectUrl ||
    conn?.data?.redirectUrl;

  console.log("\n=== OPEN THIS LINK NOW (open before doing anything else) ===\n");
  console.log(url || JSON.stringify(conn, null, 2));
  console.log("\n=========================================================\n");
}

main().catch((e) => {
  console.error("ERROR:", e?.message || e);
  process.exit(1);
});
