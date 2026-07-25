# Instagram Research Tool

Scrapes top-performing Instagram posts in any niche, screenshots each one,
transcribes every video (whisper.cpp, GPU-accelerated), and reverse-engineers
the winning patterns into a styled HTML report.

## Folder convention

Every scrape run gets **one dated folder** under `../research/`, named
`YYYY-MM-DD_<topic>` (e.g. `2026-07-09_ai-automation`). That folder holds
everything from that run: config, raw data, screenshots, transcripts, the
HTML report, and any scripts written off the back of it.

```
1g 1 million/
  ig-research/          ← this tool (scripts + whisper model, reusable)
  research/
    2026-07-09_ai-automation/   ← one scrape, fully self-contained
      config.json
      raw-posts.json
      report.html
      post-screenshots/
      hook-screenshots/
      transcripts/
      dopamine_loop_script.md   ← scripts generated FROM this data go here too
```

## Running a new scrape

1. Create `../research/<date>_<topic>/config.json`:
   ```json
   {
     "name": "Readable name",
     "niche": "description",
     "searchTerms": ["Hashtag1", "Hashtag2"],
     "competitors": ["https://www.instagram.com/handle/"],
     "browserPort": 9222,
     "maxPostsPerSearch": 8,
     "maxCompetitorPosts": 8
   }
   ```
2. Quit Chrome completely, relaunch with a dedicated debug profile:
   ```bash
   pkill -9 "Google Chrome"
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-debug-profile"
   ```
   Log into instagram.com in that window, leave it in the foreground.
3. Scrape:
   ```bash
   node scripts/scrape.js <date>_<topic>
   ```
4. Transcribe:
   ```bash
   bash scripts/transcribe.sh <date>_<topic>
   ```
5. Build the report:
   ```bash
   node scripts/report-html.js <date>_<topic>
   ```
6. Open `../research/<date>_<topic>/report.html` in **Safari** (Chrome blocks
   local `file://` → `file://` image loads by default).

## Notes

- Audio download uses `python3.13 -m yt_dlp` (not the Homebrew `yt-dlp`
  binary) because Homebrew's system Python 3.14 has a broken `pyexpat`
  module that breaks yt-dlp's XML parsing. If `python3.13` ever moves,
  update the path in `scripts/scrape.js`.
- `~/chrome-debug-profile` (a separate Chrome profile for the debug port)
  intentionally lives **outside** this project — it's an OS-level browser
  profile, not project data.
- Engagement numbers are scraped from the page DOM. The original workflow
  this tool is based on assumes a vision-capable session to hand-correct
  numbers from screenshots — that step isn't available in every environment,
  so treat DOM-scraped numbers as "good but not vision-verified."
