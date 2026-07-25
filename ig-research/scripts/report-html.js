#!/usr/bin/env node
// =============================================================================
// Instagram Research — HTML report generator
// Reads raw-posts.json (corrected in Step 9), transcripts, and hook screenshots,
// and writes a styled report.html.
// Usage: node scripts/report-html.js <project-name>
// =============================================================================
import { readFileSync, writeFileSync, existsSync, readdirSync } from 'fs';
import { join } from 'path';

const projectName = process.argv[2];
if (!projectName) {
  console.error('Usage: node scripts/report-html.js <project-name>');
  process.exit(1);
}

const projectDir = join(import.meta.dirname, '..', '..', 'research', projectName);
const rawFile = join(projectDir, 'raw-posts.json');
const transcriptsDir = join(projectDir, 'transcripts');
const hooksDir = join(projectDir, 'hook-screenshots');
const outFile = join(projectDir, 'report.html');

if (!existsSync(rawFile)) {
  console.error(`No raw-posts.json found at ${rawFile}`);
  process.exit(1);
}

const data = JSON.parse(readFileSync(rawFile, 'utf8'));
let posts = data.posts || [];

function parseNum(s) {
  if (s == null) return 0;
  if (typeof s === 'number') return s;
  const str = String(s).trim().replace(/,/g, '');
  const m = str.match(/^([\d.]+)\s*([KkMm])?/);
  if (!m) return 0;
  let n = parseFloat(m[1]);
  if (m[2]?.match(/[Kk]/)) n *= 1000;
  if (m[2]?.match(/[Mm]/)) n *= 1000000;
  return Math.round(n);
}

function fmtNum(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return String(n);
}

function esc(s) {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// attach transcript text + hook screenshots
posts = posts.map(p => {
  const txtPath = join(transcriptsDir, `${p.postId}.txt`);
  const transcript = existsSync(txtPath) ? readFileSync(txtPath, 'utf8').trim() : '';
  const hookFrames = [0, 1, 2]
    .map(s => join(hooksDir, `${p.postId}_${s}s.jpg`))
    .filter(existsSync);
  const likes = parseNum(p.likes);
  const views = parseNum(p.views);
  const comments = parseNum(p.commentsCount);
  const engagement = p.engagement && p.engagement > 0 ? p.engagement : Math.max(likes, views) + comments;
  return { ...p, transcript, hookFrames, likesNum: likes, viewsNum: views, commentsNum: comments, engagement };
});

posts.sort((a, b) => b.engagement - a.engagement);

// ---------- winning-pattern analysis ----------
function analyzeWhyItWorked(p) {
  const reasons = [];
  const hook = (p.hook || '').toLowerCase();
  const caption = (p.caption || p.fullCaption || '').toLowerCase();
  const transcript = (p.transcript || '').toLowerCase();
  const text = `${hook} ${caption} ${transcript}`;

  if (/comment\s+["'\w]+|dm\s+me|link in bio/.test(caption)) reasons.push('Comment/DM-bait CTA drives algorithmic engagement');
  if (/\d+/.test(hook)) reasons.push('Specific number in the hook builds credibility and curiosity');
  if (/framework|method|system|blueprint|playbook/.test(text)) reasons.push('Named framework signals authority and repeatability');
  if (hook.split(/\s+/).length > 0 && hook.split(/\s+/).length <= 12) reasons.push('Short, punchy hook (≤12 words) minimizes scroll-past risk');
  if (/^(why|what|how|who|is|are|do|does|can|will)\b/.test(hook)) reasons.push('Question-format hook creates an open loop');
  if (p.engagement >= 100000) reasons.push('High absolute engagement — validated by the algorithm at scale');
  if (/vs\.?|versus|instead of|compared to/.test(text)) reasons.push('Comparison framing creates a clear before/after or right/wrong contrast');
  if (/in \d+\s*(seconds|minutes|hours|days|weeks)/.test(text)) reasons.push('Time-bound promise sets a concrete, believable payoff');
  if (reasons.length === 0) reasons.push('Strong visual hook and consistent niche relevance for the target audience');
  return reasons;
}

function inferVisualHook(p) {
  const text = `${(p.caption || '')} ${(p.transcript || '')}`.toLowerCase();
  if (/split screen|side by side/.test(text)) return 'Split-screen comparison';
  if (/whiteboard|marker|draw/.test(text)) return 'Whiteboard / hand-drawn explainer';
  if (/screen record|screen share|my screen/.test(text)) return 'Screen recording walkthrough';
  if (/text overlay|bold text|caption on screen/.test(text)) return 'Talking head with bold text overlay';
  if (p.type === 'image') return 'Static slide with text overlay';
  return 'Talking head with text overlay';
}

for (const p of posts) {
  p.whyItWorked = analyzeWhyItWorked(p);
  p.visualHook = p.visualHook || inferVisualHook(p);
}

const top = posts.slice(0, 6);

// ---------- winning patterns summary ----------
const reelCount = posts.filter(p => p.type === 'reel').length;
const imageCount = posts.filter(p => p.type === 'image').length;
const ctaCount = posts.filter(p => /comment\s+["'\w]+|dm\s+me/i.test(p.caption || '')).length;
const questionHooks = posts.filter(p => /^(why|what|how|who|is|are|do|does|can|will)\b/i.test((p.hook || '').trim())).length;
const avgHookWords = posts.length
  ? Math.round(posts.reduce((sum, p) => sum + (p.hook || '').split(/\s+/).filter(Boolean).length, 0) / posts.length)
  : 0;
const transcribedCount = posts.filter(p => p.transcript).length;
const visualHookCount = posts.filter(p => p.hookFrames.length > 0).length;
const topLikes = posts.length ? Math.max(...posts.map(p => p.likesNum || 0)) : 0;

function postCard(p, rank) {
  const engStr = fmtNum(p.engagement);
  const likesStr = p.likesNum ? fmtNum(p.likesNum) : '—';
  const viewsStr = p.viewsNum ? fmtNum(p.viewsNum) : '—';
  const commentsStr = p.commentsNum ? fmtNum(p.commentsNum) : '—';
  const frames = p.hookFrames.map(f => {
    const rel = 'file://' + f;
    return `<img src="${rel}" class="frame" loading="lazy" alt="hook frame">`;
  }).join('');
  const transcriptHtml = p.transcript
    ? `<div class="transcript-box">${esc(p.transcript)}</div>`
    : `<div class="transcript-box muted">No transcript (image/carousel or audio unavailable)</div>`;
  const whyHtml = p.whyItWorked.map(w => `<li>${esc(w)}</li>`).join('');

  return `
  <div class="post-card">
    <div class="post-rank">#${rank}</div>
    <div class="post-head">
      <div class="post-author">@${esc(p.author || 'unknown')}</div>
      <div class="post-type">${esc(p.type)}${p.slideHook ? ' · slide hook' : ''}</div>
    </div>
    <div class="post-stats">
      <span>❤️ ${likesStr}</span>
      <span>👁 ${viewsStr}</span>
      <span>💬 ${commentsStr}</span>
      <span class="eng">⚡ ${engStr} engagement</span>
    </div>
    ${frames ? `<div class="frames">${frames}</div>` : ''}
    <div class="visual-hook">🎬 ${esc(p.visualHook)}</div>
    <div class="hook-quote">"${esc(p.hook || '(no hook captured)')}"</div>
    ${transcriptHtml}
    <div class="why-box">
      <div class="why-title">Why it worked</div>
      <ul>${whyHtml}</ul>
    </div>
    <div class="caption-preview">${esc((p.caption || '').slice(0, 220))}${(p.caption || '').length > 220 ? '…' : ''}</div>
    <a class="post-link" href="${esc(p.url || p.href)}" target="_blank">Open on Instagram →</a>
  </div>`;
}

const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${esc(data.project || projectName)} — Instagram Research Report</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root { --bg:#0A0A08; --gold:#D4A843; --card:#151512; --border:#262620; --text:#EDEDE6; --muted:#8a8a7f; }
  * { box-sizing: border-box; margin:0; padding:0; }
  body { font-family:'Inter',sans-serif; background:var(--bg); color:var(--text); line-height:1.6; }
  .hero { padding:4rem 2rem 3rem; text-align:center; border-bottom:1px solid var(--border);
          background:radial-gradient(ellipse at top, rgba(212,168,67,0.08), transparent 60%); }
  .hero .badge { color:var(--gold); font-size:0.75rem; letter-spacing:0.15em; text-transform:uppercase; font-weight:700; margin-bottom:1rem; }
  .hero h1 { font-size:2.2rem; font-weight:800; margin-bottom:0.5rem; }
  .hero .sub { color:var(--muted); font-size:0.95rem; }
  .hero .meta { margin-top:1rem; color:var(--muted); font-size:0.85rem; }
  .stats-bar { display:flex; justify-content:center; gap:2.5rem; flex-wrap:wrap; padding:2rem; border-bottom:1px solid var(--border); }
  .stat { text-align:center; }
  .stat .num { font-size:1.8rem; font-weight:800; color:var(--gold); }
  .stat .label { font-size:0.72rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.08em; margin-top:0.25rem; }
  .section-title { text-align:center; font-size:1.4rem; font-weight:700; margin:3rem 0 2rem; }
  .posts-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:1.5rem; max-width:1400px; margin:0 auto; padding:0 2rem; }
  .post-card { background:var(--card); border:1px solid var(--border); border-radius:1rem; padding:1.4rem; position:relative;
               transition:transform 0.2s, border-color 0.2s; }
  .post-card:hover { transform:translateY(-3px); border-color:var(--gold); }
  .post-rank { position:absolute; top:-0.7rem; left:1.2rem; background:var(--gold); color:#000; font-weight:800;
               font-size:0.8rem; padding:0.2rem 0.6rem; border-radius:999px; }
  .post-head { display:flex; justify-content:space-between; align-items:baseline; margin-top:0.6rem; margin-bottom:0.6rem; }
  .post-author { font-weight:700; }
  .post-type { color:var(--muted); font-size:0.78rem; text-transform:uppercase; letter-spacing:0.05em; }
  .post-stats { display:flex; gap:1rem; font-size:0.85rem; color:var(--muted); margin-bottom:0.8rem; flex-wrap:wrap; }
  .post-stats .eng { color:var(--gold); font-weight:600; }
  .frames { display:flex; gap:0.4rem; margin-bottom:0.8rem; }
  .frame { width:33.3%; border-radius:0.5rem; object-fit:cover; aspect-ratio:9/16; }
  .visual-hook { font-size:0.8rem; color:var(--muted); margin-bottom:0.5rem; }
  .hook-quote { font-size:1.05rem; font-weight:600; color:var(--gold); margin-bottom:0.7rem; font-style:italic; }
  .transcript-box { max-height:120px; overflow-y:auto; font-size:0.82rem; color:#c9c9bc; background:#0e0e0c;
                     border:1px solid var(--border); border-radius:0.5rem; padding:0.7rem; margin-bottom:0.8rem; }
  .transcript-box.muted { color:var(--muted); font-style:italic; }
  .why-box { background:rgba(212,168,67,0.06); border:1px solid rgba(212,168,67,0.25); border-radius:0.5rem;
             padding:0.7rem 0.9rem; margin-bottom:0.8rem; }
  .why-title { font-size:0.75rem; text-transform:uppercase; letter-spacing:0.05em; color:var(--gold); font-weight:700; margin-bottom:0.4rem; }
  .why-box ul { padding-left:1.1rem; font-size:0.83rem; color:#d8d8cc; }
  .caption-preview { font-size:0.8rem; color:var(--muted); margin-bottom:0.8rem; }
  .post-link { color:var(--gold); text-decoration:none; font-size:0.82rem; font-weight:600; }
  .post-link:hover { text-decoration:underline; }
  .patterns-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:1.2rem; max-width:1100px; margin:0 auto 3rem; padding:0 2rem; }
  .pattern-card { background:var(--card); border:1px solid var(--border); border-radius:0.8rem; padding:1.2rem; }
  .pattern-card h3 { font-size:0.85rem; color:var(--gold); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.6rem; }
  .pattern-card p { font-size:0.88rem; color:#d8d8cc; }
  footer { text-align:center; padding:3rem 2rem; color:var(--muted); font-size:0.8rem; border-top:1px solid var(--border); margin-top:2rem; }
  footer a { color:var(--gold); }
</style>
</head>
<body>

<div class="hero">
  <div class="badge">Instagram Research Report</div>
  <h1>${esc(data.project || projectName)}</h1>
  <div class="sub">${esc(data.niche || '')}</div>
  <div class="meta">
    Search terms: ${(data.searchTerms || []).map(esc).join(', ') || '—'}
    ${data.competitors?.length ? ' · Competitors: ' + data.competitors.map(c => esc(c)).join(', ') : ''}
    · Scraped ${esc(new Date(data.scrapedAt || Date.now()).toLocaleDateString())}
  </div>
</div>

<div class="stats-bar">
  <div class="stat"><div class="num">${posts.length}</div><div class="label">Total Posts</div></div>
  <div class="stat"><div class="num">${posts.length ? Math.round((reelCount / posts.length) * 100) : 0}%</div><div class="label">Reels</div></div>
  <div class="stat"><div class="num">${transcribedCount}</div><div class="label">Transcribed</div></div>
  <div class="stat"><div class="num">${visualHookCount}</div><div class="label">Visual Hooks Captured</div></div>
  <div class="stat"><div class="num">${fmtNum(topLikes)}</div><div class="label">Top Likes</div></div>
</div>

<div class="section-title">Top ${top.length} Performing Posts</div>
<div class="posts-grid">
  ${top.map((p, i) => postCard(p, i + 1)).join('\n')}
</div>

<div class="section-title">Winning Patterns</div>
<div class="patterns-grid">
  <div class="pattern-card">
    <h3>Format breakdown</h3>
    <p>${reelCount} reels (${posts.length ? Math.round((reelCount / posts.length) * 100) : 0}%) vs ${imageCount} images/carousels. ${reelCount > imageCount ? 'Reels dominate — spoken hooks and motion drive this niche.' : 'Static/carousel content holds its own — slide-based hooks matter here.'}</p>
  </div>
  <div class="pattern-card">
    <h3>Comment-bait CTAs</h3>
    <p>${ctaCount} of ${posts.length} top posts (${posts.length ? Math.round((ctaCount / posts.length) * 100) : 0}%) use a "comment a word" or DM-based CTA — this is the single most repeatable engagement lever in the data.</p>
  </div>
  <div class="pattern-card">
    <h3>Hook analysis</h3>
    <p>Average hook length: ${avgHookWords} words. ${questionHooks} posts open with a question-format hook, creating an immediate open loop.</p>
  </div>
  <div class="pattern-card">
    <h3>Content themes</h3>
    <p>Niche: ${esc(data.niche || '—')}. Winning posts consistently pair a specific, credible claim (numbers, named frameworks) with a fast visual or spoken payoff in the first 3 seconds.</p>
  </div>
</div>

<footer>
  Generated by the Instagram Research Tool · Reverse-engineered, not guessed.
</footer>

</body>
</html>`;

writeFileSync(outFile, html);
console.log(`Report written → ${outFile}`);
