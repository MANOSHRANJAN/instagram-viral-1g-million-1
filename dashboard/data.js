// =============================================================================
// Dashboard data source. Edit this file to update goal numbers, account info,
// and analytics. Ask Kiro to update it whenever you have new real numbers —
// or edit the fields directly, they're plain JS/JSON.
// =============================================================================
window.DASHBOARD_DATA = {

  // ---- GOAL AGENT ----
  goal: {
    target: 100000,
    startDate: "2026-07-13",   // day 1 of the 90-day plan
    durationDays: 90,
    currentFollowers: 0,       // update after the new account is live
    note: "New account, 0 → 100K in 90 days. See content/growth_strategy_0to100k_90days.md for the honest math — 100K is the stretch case, 20-40K organic is the realistic floor without paid boost + breakout."
  },

  // ---- ACCOUNT AGENT ----
  account: {
    handle: "@TBD — not yet created",
    followingCount: 0,
    status: "Account not created yet. Confirm handle name to activate this section.",
    lastChecked: null
  },

  // ---- CONTENT AGENT: Week 1 plan (synced from content/week1_content_plan.md) ----
  week1Plan: [
    { day: 1, pillar: "Founder / Build-in-public", hook: "I built an AI agency with zero coding.", cta: "FOLLOW", note: "Pinned intro post" },
    { day: 2, pillar: "AI Shifts & Big Ideas", hook: "AI just made your degree worthless.", cta: "SHIFT", note: "Reach play" },
    { day: 3, pillar: "Tool & Automation Breakdown", hook: "Five AI tools replacing entire teams.", cta: "STACK", note: "Reach play" },
    { day: 4, pillar: "Proof / Demo", hook: "This AI just booked a real patient.", cta: "BOND", note: "Convert — your unfair advantage" },
    { day: 5, pillar: "Contrarian Hot Take", hook: "Human receptionists are a luxury now.", cta: "(comment agree/disagree)", note: "Comment-bait, reach" },
    { day: 6, pillar: "AI Shifts & Big Ideas", hook: "AI didn't get smarter this year. It got dangerous.", cta: "FOLLOW", note: "Check trending_topics.md first — swap for live newsjack if available" },
    { day: 7, pillar: "Case Study / Results", hook: "Before AI: 11 missed calls a day. After: zero.", cta: "WORKFLOW", note: "Save-driver, convert" }
  ],

  // ---- OPS AGENT: daily checklist (repeats every day, resets at midnight) ----
  dailyChecklist: [
    "Film / post today's reel (see Content Agent below)",
    "Cross-post same reel to TikTok + YouTube Shorts",
    "Reply to every comment in the first 60 minutes",
    "Check content/trending_topics.md for a live newsjack opportunity",
    "Log today's post stats in the Analytics Agent below",
    "Script tomorrow's reel before end of day"
  ],

  // ---- ANALYTICS AGENT: manual log, seed empty until real data exists ----
  // Add entries via the "Log today's numbers" form (saved to your browser's
  // localStorage) or paste real scrape data here directly.
  analyticsLog: [
    // { date: "2026-07-13", followers: 0, views: 0, likes: 0, comments: 0, saves: 0, newFollowers: 0 }
  ],

  // ---- DAY PLAYBOOKS: full production detail per day (opened via "Playbook" button) ----
  dayPlaybooks: {
    1: {
      title: "Founder Intro — Pinned Post",
      pillar: "Founder / Build-in-public",
      goal: "The first video anyone sees on the profile. Job: make a stranger understand who you are + what you build + why follow, in under 30s. This gets pinned.",
      postingWindow: "8–10am your local time (test window). Pin immediately after posting.",

      // shot-by-shot reel script
      reel: {
        format: "Talking-head + light B-roll · vertical 9:16 · 25–30s",
        deliveryNote: "Shoot all talking-head lines in ONE take, eye-level, window light on your face. Speak slightly faster than feels natural — energy reads as confidence. Drop B-roll over the marked beats in editing.",
        shots: [
          { time: "0:00–0:03", camera: "Close-up, slow push-in", dialogue: "I build the systems that get local businesses more clients — and I'm doing it in public.", onScreen: "WEBSITES + ADS + AI", broll: "Face to camera, clean uncluttered background", edit: "Hard cut in. Subtle motion blur on the push-in.", pause: "Beat (0.3s) after 'clients' before 'and I'm doing it in public' — the pause makes the second half land." },
          { time: "0:03–0:10", camera: "Medium", dialogue: "Three things: websites that convert, AI ads that find the right person, and AI that never misses a lead.", onScreen: "3 PILLARS. 1 SYSTEM.", broll: "Quick cuts: site mockup → ad dashboard → AI call transcript", edit: "One cut per pillar as you say it. Snappy.", pause: "Tiny beat between each of the 'three things' — list rhythm." },
          { time: "0:10–0:18", camera: "Screen recording", dialogue: "This is the one I'm proudest of — an AI receptionist that answers every call, 24/7.", onScreen: "NEVER MISSES A LEAD", broll: "Screen-rec of the AI booking a real appointment", edit: "Speed-ramp the screen scroll. Soft 'ding' SFX on the booking.", pause: "Let the screen-rec breathe — 1s of just the demo with no talking." },
          { time: "0:18–0:25", camera: "Handheld", dialogue: "I'm posting the real builds, real numbers, no fluff — every day this month.", onScreen: "REAL BUILDS. REAL NUMBERS.", broll: "Walking shot, natural movement", edit: "Handheld sway for authenticity. No stabilization.", pause: "Punch 'every day this month' — slow down on those 4 words." },
          { time: "0:25–0:30", camera: "Close-up (CTA)", dialogue: "Follow along — day one of building this in public.", onScreen: "💬 FOLLOW · DAY 1", broll: "Back to talking head, direct eye contact", edit: "Zoom-out to end card. Follow-icon pop.", pause: "Hold eye contact for 0.5s of silence at the very end before cut — stops the scroll-away." }
        ],
        caption: "Day 1. Building AI systems for local businesses, in public. Websites, AI ads, AI that never misses a lead. Follow the build. 👇 #buildinpublic #aiautomation #founder #aiagency",
        audio: "Low-energy trending audio bed under the VO (keep it at ~10% volume so your voice leads). Check the Reels audio tab for a rising trending track that day."
      },

      // carousel companion (repurpose the reel hook as a static carousel for extra surface area)
      carousel: {
        purpose: "Repurpose Day 1's message as a 6-slide carousel — different surface, saves + profile visits, no extra filming.",
        style: "Dark background (#0A0A08), gold accent (#D4A843), one big bold line per slide, your face on slide 1 and slide 6.",
        slides: [
          { n: 1, headline: "I build the systems that get businesses more clients.", sub: "And I'm documenting all of it.", visual: "Your photo, bold text overlay" },
          { n: 2, headline: "Pillar 1 — Websites that convert.", sub: "Not just pretty. Built to book.", visual: "Before/after site screenshot" },
          { n: 3, headline: "Pillar 2 — AI ads.", sub: "Find the right buyer, cheap.", visual: "Ad dashboard screenshot" },
          { n: 4, headline: "Pillar 3 — AI that never misses a lead.", sub: "Answers every call, 24/7.", visual: "AI receptionist call transcript" },
          { n: 5, headline: "One system. Get found → get booked → never lose the lead.", sub: "", visual: "Simple 3-step diagram" },
          { n: 6, headline: "Following the whole build, in public.", sub: "Tap follow — this is day 1.", visual: "Your photo + follow arrow" }
        ],
        caption: "Same as the reel caption — or shorten to: 'Day 1. Here's exactly what I'm building in public 👇 Follow for the real numbers.'"
      },

      // how to shoot
      howToShoot: {
        setup: [
          "Phone vertical, chest height, lens at eye level (prop it on books/tripod).",
          "Sit/stand ~1m from a window — window to your FACE, never behind you.",
          "Clean background: a wall, a plant, a shelf. No messy bed/clutter.",
          "Wipe your lens. Seriously — smudged lens kills perceived quality instantly."
        ],
        settings: [
          "Record 4K 30fps if your phone allows, otherwise 1080p 30fps.",
          "Lock exposure + focus on your face (tap-and-hold on iPhone) so it doesn't hunt.",
          "Airplane mode on — no notification interruptions mid-take."
        ],
        delivery: [
          "Do 3 full takes minimum. Pick the one where your energy is highest, not the 'cleanest'.",
          "Look INTO the lens, not at yourself on screen.",
          "Slightly faster pace + slightly more energy than feels natural — the camera flattens energy.",
          "Use the pause notes in the script — the beats are what make it feel intentional, not rushed."
        ],
        broll: [
          "Screen-record the AI receptionist actually booking an appointment (this is your strongest 8 seconds — get it clean).",
          "One walking shot outdoors or through a doorway for the 'handheld' beat.",
          "A site mockup + ad dashboard on screen for the '3 pillars' cuts.",
          "Keep every B-roll clip 2–3s max. New visual every few seconds = retention."
        ],
        editing: [
          "Burn in captions (bold, center-lower). Silent autoplay is the default — no captions = no watch.",
          "Cut all dead air and 'um's. First frame must have motion or a face already talking.",
          "End card: your handle + 'Follow · Day 1' held for the last 0.5s."
        ]
      },

      // data points / what to track
      dataPoints: {
        whyItWorks: [
          "'I built an AI agency with zero coding' removes the biggest objection viewers have → they think 'then I could too'.",
          "Naming 3 concrete pillars in one breath signals competence without sounding scattered.",
          "The live screen-rec is proof, not claim — proof out-converts every hook in your scrape data.",
          "'Day 1 / in public' creates an open loop: people follow to see day 2, 3, 10."
        ],
        targetMetrics: [
          "Hook rate (viewers past 3s): aim >70%.",
          "Avg watch %: aim >50% (it's short, so achievable).",
          "This is a baseline post — don't expect virality. Its job is to convert profile-visitors into followers, not to blow up.",
          "Profile-visit → follow rate is the number that matters most here since it's pinned."
        ],
        firstHour: [
          "Reply to every single comment within 60 minutes.",
          "Share to your story with a 'Day 1 👀' sticker to drive the first views.",
          "DM it to anyone who'd genuinely engage — first-hour engagement velocity feeds the algorithm."
        ]
      }
    }
  },

  // ---- RESEARCH AGENT: quick links to source docs (relative to dashboard/) ----
  links: [
    { label: "90-Day Growth Strategy (0→100K)", href: "../content/growth_strategy_0to100k_90days.md" },
    { label: "Week 1 Content Plan (full scripts)", href: "../content/week1_content_plan.md" },
    { label: "Account Positioning", href: "../content/account_positioning.md" },
    { label: "Hook Bank (30+ hooks)", href: "../content/hook_bank.md" },
    { label: "Trending Topics / Newsjacks", href: "../content/trending_topics.md" },
    { label: "7-Day Content Strike (agency angle)", href: "../content/7_day_content_strike.md" },
    { label: "IG Research Report (40-post scrape)", href: "../research/2026-07-09_ai-automation/report.html" },
    { label: "Dopamine Loop Script", href: "../research/2026-07-09_ai-automation/dopamine_loop_script.md" }
  ]
};
