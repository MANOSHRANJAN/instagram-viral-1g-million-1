# Learned Patterns

> Corpus note: only one reel analysis is present ([reel #0]). True "repeating DNA" requires N≥2, so what follows is the structural signature of the single reel cross-referenced against the Algorithm Bible. Where I'd normally show a pattern repeating across reels, I instead show the pattern present in [reel #0] plus the Bible rule that predicts whether it generalizes. Treat these as hypotheses to confirm once more reels load.

## Hook Formulas That Repeat

Single-reel corpus, so these are the formulas *observed*, not yet *confirmed-repeating*. Each is grounded in a Bible rule that explains the mechanism.

1. The "Still Doing X" Call-Out + Loss-Frame
   - Example: "if you're still doing cold outreach... [as a video editor] you're falling behind in 2025" [reel #0]
   - Why it works (Bible): Brock's H — negative framing stops the scroll, and Brock's "controversial/timely" share-driver lets viewers silently align with the stance. Mosseri's timely/newsworthy angle is triggered by the "in 2025" timestamp. The mechanism is status threat: it names a behavior the viewer is doing and frames it as falling behind.

2. The Identity-Tag Hook ("as a [role]")
   - Example: "as a video editor" inserted mid-hook to pin the exact ICP [reel #0]
   - Why it works (Bible): Brock's R — Relatable through specificity. Naming the role makes the right viewer feel directly addressed, which Mosseri's send>save ranking rewards because it becomes "this is literally you" DM-able.

3. The Time-Stamped Urgency Tag ("in 2025")
   - Example: "you're falling behind in 2025" [reel #0]
   - Why it works (Bible): Mosseri's timely/newsworthy lever plus Brock's E — a deadline-flavored frame adds stakes without adding words.

## Structural Skeletons That Repeat

The observed skeleton in [reel #0] is:

Call-out → Identity tag → Threat/loss → Time stamp → Label re-emphasis

So: "if you're still doing cold outreach" → "as a video editor" → "you're falling behind" → "in 2025" → "cold outreach" again [reel #0].

Critically, this is a hook-only loop. The analysis flags `fulfills_hook_promise: false` and `reinforcement_cycles_count: 1` [reel #0]. This is NOT the Hormozi skeleton (hook → question → hammer → example). It's a single loss-loop that teases without paying off. The Bible predicts this collapses retention: Mosseri tracks total watch time, and a tease with no delivered value can't hold 38 seconds [reel #0].

## Visual / Cut Patterns

- Kinetic text, word-by-word fade-in over a phone/DM mockup [reel #0].
- Fast pacing: `cuts_per_10s_estimate: 6`, which clears Brock/Hormozi's "cut every 2s or faster" bar [reel #0].
- The killer flaw: near-black screen, low-contrast text "barely legible against the dark background" [reel #0]. This violates Brock's "drunk grandma" simplicity rule — the hook is physically hard to read in the first second, which the analysis names as "the single biggest reach killer here" [reel #0].

Pattern to carry forward: fast kinetic text works; dark/low-contrast text does not.

## SFX / Audio Patterns

No audio data is present in [reel #0] (`transcript_excerpt` is empty and frames show silent kinetic text only). The reel reads as a silent text-overlay template. Nothing to confirm on trending audio, BPM, or voiceover. This is a gap — load more reels to establish an audio pattern.

## Comment / Engagement Driver Patterns

- Contrarian / hard-stance driver: the "cold outreach is dead, you're falling behind" angle is a controversial opinion, which Brock lists as a share trigger (people share to silently align) [reel #0].
- Broadcast shareability passes weakly, but `send_worthy_to_one_person: false` — there's no "this is you" specificity worth a 1:1 DM, which is the send Mosseri values most [reel #0].
- No keyword-DM mechanic, no explicit "send this to..." CTA. `cta_placement: none` and `cta_present: false` [reel #0]. Brock calls "ask for the share" the single most underused tactic — it's entirely absent here.

## What's Working in THIS Avatar's Niche (vs general virality)

The locked avatar is Mike, a 38yo plumbing business owner, tech-scared, losing leads to voicemail [reel #0]. Nothing in [reel #0] serves Mike — it targets video editors doing cold outreach. The analysis hard-gates it: `audience_match score 1/25`, `topic_drift_warning` flags "Wrong industry, wrong pain, wrong intent," and the leaks note the score is "capped at 60 and cascade dies" [reel #0].

So what actually works for Mike isn't in the source reel — it's in the transferable remixes [reel #0]:
- Trade-specific loss-framing beats generic AI/freelancer fear: "if you're still letting calls go to voicemail in 2025, you're handing jobs to the next plumber."
- Concrete, visual pain (a 7pm missed-call screen, then the lost-job math) earns the 1:1 send Mosseri prizes, where a vague "falling behind" does not.
- A save-worthy payoff (3-step "never miss a lead" setup: auto-text-back + missed-call workflow) fulfills the hook promise and earns saves — the exact things [reel #0] failed to do.

## What's NOT Working (consistent leaks)

From [reel #0], the recurring score-killers:
1. Hook promise never paid off — frames show only the threat, no solution; `hook_promise_kept_in_body: false` (Hormozi: fulfill the promise) [reel #0].
2. Unreadable visual — near-black, low-contrast text breaks Brock's "drunk grandma" rule and kneecaps the first-second grab [reel #0].
3. Topic drift / wrong avatar — hard gate; serves video editors, not Mike [reel #0].
4. No CTA at all — `cta_present: false`, ignoring Brock's "ask for the share" [reel #0].
5. Vague over specific — "falling behind" with no number or mechanism fails Brock's R [reel #0].
6. Aggregation over originality — "generic dark kinetic-text template with a recycled fearmonger angle" fails Mosseri's originality reward [reel #0].

## 5 Hook Templates the User Can Reuse Tomorrow

All rewritten for Mike the plumbing-business owner, derived from the formulas in [reel #0].

1. Still-Doing Loss-Frame (from formula #1)
   "If you're still letting calls go to voicemail in [year], you're handing jobs to the next plumber." [reel #0]

2. Identity-Tag Call-Out (from formula #2)
   "As a [plumbing / HVAC / electrical] business owner, the lead you missed at 7pm just called your competitor." [reel #0]

3. Myth-Bust Contrarian (from the controversial-share driver)
   "Cold calling for plumbing leads is dead — here's what actually books trucks now." [reel #0]

4. Specific-Scenario Relatable (from Brock's R + send>save)
   "It's 7:14pm, a $4,000 water-heater job calls, you're elbow-deep in a sink — here's how you still book it." [reel #0]

5. Time-Stamped Power Promise (from formula #3 + save value)
   "The 3-step setup that stopped me losing one job a week to voicemail in [year]." [reel #0]

## How the Writer Should Use These Patterns

When generating 3 script variations, pull 3 genuinely different hook formulas and 3 different structures so the variations don't collapse into the same reel. For example: variation A uses the Still-Doing Loss-Frame (template 1) with a Hormozi hook→question→hammer→example skeleton that actually delivers the missed-call fix; variation B uses the Myth-Bust Contrarian (template 3) with a problem→proof→payoff structure built for silent-alignment shares; variation C uses the Specific-Scenario Relatable (template 4) with a story→stakes→solution arc engineered for the 1:1 send. Across all three, fix the two leaks that sank [reel #0]: pair every hook with a bright, high-contrast, readable visual (Brock's drunk-grandma rule), and always fulfill the promise with a save-worthy payoff plus an explicit "send this to the partner who keeps missing calls" CTA (Hormozi fulfill-the-promise + Brock ask-for-the-share).