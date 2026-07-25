"""Hit the Kiro API directly and write results to HTML."""
import json, time, datetime, urllib.request, urllib.error, ssl, os
from pathlib import Path

# ── load kiro.env ──
env_path = Path(__file__).parent / "kiro.env"
cfg = {}
for line in env_path.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        cfg[k.strip()] = v.strip().strip('"').strip("'")

API_KEY  = cfg.get("ANTHROPIC_API_KEY", "")
BASE_URL = cfg.get("ANTHROPIC_BASE_URL", "https://api.kiro.dev").rstrip("/")
MODEL    = cfg.get("CLAUDE_MODEL", "claude-sonnet-4-5")
URL      = f"{BASE_URL}/v1/messages"

# ── disable any proxy ──
os.environ.pop("https_proxy", None)
os.environ.pop("http_proxy", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("HTTP_PROXY", None)
os.environ["no_proxy"] = "*"

# ── call the API ──
payload = json.dumps({
    "model": MODEL,
    "max_tokens": 60,
    "messages": [{"role": "user", "content": "Reply with exactly: KIRO API IS WORKING"}]
}).encode()

headers = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}

status  = "FAILED"
reply   = ""
latency = 0
error   = ""
raw     = ""
http_code = 0

ctx = ssl.create_default_context()
try:
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
except:
    pass

# Bypass any system proxy
no_proxy = urllib.request.ProxyHandler({})
opener   = urllib.request.build_opener(no_proxy)

t0 = time.time()
try:
    req = urllib.request.Request(URL, data=payload, headers=headers, method="POST")
    with opener.open(req, timeout=30, context=ctx) if hasattr(opener, '__call__') else opener.open(req, timeout=30) as r:
        raw = r.read().decode()
        http_code = r.status
        latency = round((time.time() - t0) * 1000)
        j = json.loads(raw)
        blocks = j.get("content", [])
        reply = " ".join(b.get("text","") for b in blocks if b.get("type")=="text").strip()
        status = "SUCCESS" if reply else "NO_REPLY"
        if not reply:
            error = f"No text blocks in response"
except urllib.error.HTTPError as e:
    latency = round((time.time() - t0) * 1000)
    http_code = e.code
    try: raw = e.read().decode()[:500]
    except: pass
    error = raw or str(e)
except Exception as ex:
    latency = round((time.time() - t0) * 1000)
    error = str(ex)

now = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")

# ── print results ──
print(f"Endpoint: {URL}")
print(f"Model:    {MODEL}")
print(f"Status:   {status}")
print(f"Latency:  {latency}ms")
if reply:  print(f"Reply:    {reply}")
if error:  print(f"Error:    {error}")

# ── build HTML ──
ok = status == "SUCCESS"
C = "#22c55e" if ok else "#ef4444"
BG = "#052e16" if ok else "#2d0a0a"
ICON = "✅" if ok else "❌"

escaped_raw = raw.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")[:800] if raw else "(none)"
escaped_err = error.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") if error else ""
masked_key  = f"{API_KEY[:8]}···{API_KEY[-4:]}" if len(API_KEY) > 12 else API_KEY

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kiro API Test</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:#09090b;color:#fafafa;min-height:100vh;display:grid;place-items:center;padding:2rem}}
.card{{background:#18181b;border:1px solid #27272a;border-radius:1.5rem;max-width:760px;width:100%;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.6);animation:fadeIn .4s ease both}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
.hdr{{padding:2rem 2.5rem 1.5rem;border-bottom:1px solid #27272a;background:linear-gradient(135deg,#1e1b4b 0%,#18181b 60%)}}
.badge{{font-size:.72rem;font-weight:700;letter-spacing:.15em;color:#818cf8;text-transform:uppercase;margin-bottom:.4rem}}
h1{{font-size:1.6rem;font-weight:800}}
.ts{{font-size:.78rem;color:#71717a;margin-top:.3rem}}
.banner{{margin:1.5rem 2.5rem;padding:1.1rem 1.3rem;border-radius:.85rem;border:1px solid {C}33;background:{BG};display:flex;align-items:center;gap:.85rem}}
.dot{{width:14px;height:14px;border-radius:50%;background:{C};box-shadow:0 0 12px {C};flex-shrink:0;animation:pulse 2s ease infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.5}}}}
.banner-text{{font-size:1.1rem;font-weight:700;color:{C}}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:.8rem;padding:1.25rem 2.5rem}}
.kv{{background:#09090b;border:1px solid #27272a;border-radius:.65rem;padding:.85rem 1rem}}
.kv-l{{font-size:.68rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#71717a;margin-bottom:.25rem}}
.kv-v{{font-family:'JetBrains Mono',monospace;font-size:.82rem;word-break:break-all}}
.kv-v.ok{{color:#4ade80}}.kv-v.err{{color:#f87171}}
.sec{{padding:1.25rem 2.5rem}}
.sec-title{{font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#71717a;margin-bottom:.75rem}}
.reply{{background:#0a1a0f;border:1px solid #14532d;border-radius:.75rem;padding:1.2rem;font-family:'JetBrains Mono',monospace;font-size:1rem;color:#4ade80;line-height:1.6}}
.err-box{{background:#1c0505;border:1px solid #7f1d1d55;border-radius:.75rem;padding:1rem;font-family:'JetBrains Mono',monospace;font-size:.82rem;color:#fca5a5;word-break:break-all;white-space:pre-wrap}}
details summary{{cursor:pointer;font-size:.72rem;color:#52525b;padding:.5rem 0;list-style:none;user-select:none}}
details summary::-webkit-details-marker{{display:none}}
.raw{{background:#09090b;border:1px solid #27272a;border-radius:.5rem;padding:.8rem;font-family:'JetBrains Mono',monospace;font-size:.7rem;color:#52525b;white-space:pre-wrap;word-break:break-all;max-height:180px;overflow-y:auto;margin-top:.4rem}}
.ftr{{padding:1rem 2.5rem;border-top:1px solid #27272a;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem}}
.pill{{font-size:.7rem;padding:.25rem .7rem;border-radius:999px;background:#1e1b4b;color:#818cf8;border:1px solid #312e81}}
</style>
</head>
<body>
<div class="card">
  <div class="hdr">
    <div class="badge">🔬 Kiro API Test</div>
    <h1>Claude via Kiro</h1>
    <div class="ts">{now}</div>
  </div>
  <div class="banner">
    <div class="dot"></div>
    <div class="banner-text">{ICON} {status}</div>
  </div>
  <div class="grid">
    <div class="kv"><div class="kv-l">Endpoint</div><div class="kv-v">{BASE_URL}</div></div>
    <div class="kv"><div class="kv-l">Model</div><div class="kv-v">{MODEL}</div></div>
    <div class="kv"><div class="kv-l">API Key</div><div class="kv-v">{masked_key}</div></div>
    <div class="kv"><div class="kv-l">Latency</div><div class="kv-v {'ok' if ok else 'err'}">{latency} ms</div></div>
  </div>
  {"<div class='sec'><div class='sec-title'>Model Reply</div><div class='reply'>" + reply + "</div></div>" if reply else ""}
  {"<div class='sec'><div class='sec-title'>Error</div><div class='err-box'>" + escaped_err + "</div></div>" if error else ""}
  <div class="sec">
    <details><summary>▶ Raw response</summary><div class="raw">{escaped_raw}</div></details>
  </div>
  <div class="ftr">
    <div class="pill">anthropic-version: 2023-06-01</div>
    <div class="pill">HTTP {http_code if http_code else 'N/A'}</div>
  </div>
</div>
</body>
</html>"""

out = Path(__file__).parent / "kiro_api_result.html"
out.write_text(html)
print(f"\n📄 Report: {out}")
