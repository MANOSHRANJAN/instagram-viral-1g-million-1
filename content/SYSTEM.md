# The Virality System — July: 1M views + 10K followers

Your full toolkit. No guesswork — we ingest what actually works, reverse-engineer it, and ship.

---

## 1. SWIPE FILE — reverse-engineer proven winners (no guessing)
Ingest real viral videos → pulls real views + transcript (via yt-dlp) → LLM extracts hook, CTA, format, and WHY it worked.

```bash
cd virality_agent

# Add reels/shorts you want to model (paste real URLs — 1M+ view ones)
.venv/bin/python -m virality.cli swipe add -u "<url1>" -u "<url2>" -u "<url3>"

# See the collection
.venv/bin/python -m virality.cli swipe list

# Build the visual dashboard (opens in browser)
.venv/bin/python -m virality.cli swipe dashboard   # → content/swipe_dashboard.html

# Reverse-engineer the PATTERNS into a playbook
.venv/bin/python -m virality.cli swipe analyze      # → content/swipe_playbook.md
```
### Instagram reels — 2 quick prerequisites
IG blocks anonymous access and reels have no caption track, so:
1. **Log into instagram.com in Chrome** (yt-dlp reads your browser cookies automatically). This unlocks views, caption, and creator for any reel.
2. **(Optional) Add `GROQ_API_KEY`** to `elevenlabs.env` (or any .env) to auto-transcribe the *spoken* words of each reel. Without it, the swipe still captures the hook from the caption + on-screen text you can paste. Get a free key at console.groq.com.

Then just paste reel URLs:
```bash
.venv/bin/python -m virality.cli swipe add -u "https://www.instagram.com/reel/XXXX/" -u "https://www.instagram.com/reel/YYYY/"
```
Feed it 15–30 winning reels in your niche → `swipe analyze` gives you the exact hook/format/CTA patterns to copy.

(YouTube Shorts also work with zero setup — same short-form DNA — if you want extra pattern data fast.)

## 2. BRAIN — today's viral topics, auto-scripted
```bash
.venv/bin/python -m virality.cli brain -n 5    # → content/brain/DATE.md
```
Pulls today's freshest AI headlines, reverse-engineers what'll pop, writes 5 ready reels in your voice.

## 3. GENERATE / MINE — scripts from a topic or competitors
```bash
.venv/bin/python -m virality.cli mine @creator1 @creator2 --topic "your angle"
```

## 4. NARRATE — human voiceover (ElevenLabs)
```bash
.venv/bin/python -m virality.cli narrate --file content/today_story_reel.md --out content/audio/today.mp3
```
(Indian-accent / cloned voice once you upgrade ElevenLabs.)

---

## JULY PLAN → 1M views + 10K followers

**The math:** 10K followers in 30 days needs volume + at least one breakout. Target ~2 reels/day (~50 reels). If ~1 in 15 breaks out (realistic with a tuned system), a single 500K–1M reel + steady 5–20K reels compounds to 10K follows.

**Weekly loop (repeat 4x):**
1. **Mon — Mine winners.** `swipe add` 5 new 1M+ reels in your niche → `swipe analyze` → refresh the pattern playbook.
2. **Daily — Feed the brain.** `brain -n 3` for newsjack angles; pick the sharpest.
3. **Script** the day's 2 reels modeled on the top swipe patterns (hook in 1.7s, trending audio, captions, 1 keyword CTA).
4. **Batch film** 2–3x/week. Post 1–2/day at peak (test 8–10am & 6–9pm IST).
5. **Engage** hard in the first 60 min (reply to every comment — feeds the spike).
6. **Kill & clone:** any reel <40% hook-rate → drop that pattern. Any >75% or breakout → make 3 more like it immediately.

**Content mix (from the strategy doc):** ~60% reach (AI shifts, tool breakdowns, hot takes, newsjacks) · ~30% proof/demos (your dental AI receptionist) · ~10% founder story. Educate broadly, sell narrowly.

**Non-negotiables (from real data):**
- Hook lands in the first **1.7 seconds** (visual + spoken).
- **Trending audio** under every reel.
- Burned-in **captions** always.
- One clear **CTA** (follow for reach reels; keyword for proof reels).
- **Rewatch loops** — end on a line that makes them replay.

**Track weekly:** reach from non-followers %, avg watch time, saves+shares, follower conversion, which hook pattern won.

---

## Next action
Paste me 10–20 reel/short URLs you think are the best in your niche (AI, automation, creators you admire). I'll ingest them all, build the dashboard, and generate the pattern playbook — then we script the first batch off the winners.
