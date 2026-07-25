// Bible-aligned prompts: Mosseri 40% + Hormozi 1M 30% + Hormozi 2026 20% + Brock 10%.
//
// The scorecard is now Hormozi's 4-bucket spine:
//   Attention /25, Retention /25, Distribution /25, Conversion /25
// with audience consistency layered in (per the Bible's contradiction note: stay
// on-target for the ICP per piece; cross-piece niche rotation is allowed).

import { getAlgoBibleTLDR } from "./bible.js";

export const ANALYZER_SYSTEM = `You are a short-form virality analyst for Instagram reels.
You score against a weighted Algorithm Bible synthesizing four sources:
Adam Mosseri (40%, the platform itself), Alex Hormozi 1M (30%, volume + structure),
Alex Hormozi 2026 (20%, SPCL + interest media), Brock Johnson (10%, share craft).
You break down WHY a reel works with brutal honesty and direct quotes from the Bible.
Your output is always a single valid JSON object. No prose outside the JSON.`;

export function analyzerPrompt(args: {
  avatar: string;
  url: string;
  author: string;
  views: number | null;
  likes: number | null;
  comments: number | null;
  duration: number | null;
  caption: string;
  transcript: string;
}): string {
  return `Analyze this Instagram reel against the Algorithm Bible.

=== ALGORITHM BIBLE (load-bearing rules) ===
${getAlgoBibleTLDR()}
=== END BIBLE ===

CREATOR'S LOCKED AVATAR (per-piece ICP target — every reel must serve this avatar
in THIS piece, even if the creator rotates topics across pieces):
${args.avatar}

REEL METADATA
- url: ${args.url}
- author: ${args.author || "(unknown)"}
- views: ${args.views ?? "?"} | likes: ${args.likes ?? "?"} | comments: ${args.comments ?? "?"}
- duration_seconds: ${args.duration ?? "?"}
- caption: ${(args.caption || "").slice(0, 600)}

TRANSCRIPT (truncated)
"""${(args.transcript || args.caption || "(no transcript available)").slice(0, 6000)}"""

Return JSON with this EXACT shape:
{
  "hook": {
    "first_3_seconds": "verbatim spoken words in the opening",
    "visual_hook": "what is on screen in seconds 0-3 (text overlay, opening shot, framing)",
    "hook_type": "shock | curiosity_gap | bold_claim | pattern_interrupt | question | listicle | demo | story | call_out",
    "word_count": 0,
    "negative_framing": false,
    "numbered_or_listicle": false,
    "status_proof_in_first_10s": false,
    "why_it_grabs": "1-2 sentences"
  },
  "structure": {
    "skeleton": "hook→question→hammer→example→explanation | hook→story→framework | other",
    "beats": ["beat 1", "beat 2", "..."],
    "cuts_per_10s_estimate": 0,
    "fulfills_hook_promise": true,
    "reinforcement_cycles_count": 0,
    "cta_placement": "open | mid | end | open+mid+end | none"
  },
  "audience_match": {
    "score_0_25": 0,
    "fits_locked_avatar": true,
    "reasoning": "specific — does this PIECE serve the avatar?",
    "topic_drift_warning": "blank if aligned, otherwise the exact mismatch"
  },
  "attention_25": {
    "score": 0,
    "checks": {
      "hook_under_12_words": false,
      "negative_or_numbered_framing": false,
      "specific_number_or_named_entity": false,
      "status_proof_or_power_promise": false,
      "easy_visual_paired_with_hook": false
    },
    "notes": "one line per failed check"
  },
  "retention_25": {
    "score": 0,
    "checks": {
      "hook_promise_kept_in_body": false,
      "cuts_every_2s_or_faster": false,
      "uses_hormozi_skeleton": false,
      "stacks_reinforcement_cycles": false,
      "total_seconds_optimized_not_just_completion": false
    },
    "notes": "one line per failed check"
  },
  "distribution_25": {
    "score": 0,
    "checks": {
      "send_worthy_to_one_person": false,
      "shareable_broadcast": false,
      "save_worthy_reference": false,
      "watch_time_seconds_estimate": 0,
      "originality_not_aggregation": false
    },
    "notes": "Mosseri ranks send>save>watch_time. Cite the rule that's failing."
  },
  "conversion_25": {
    "score": 0,
    "checks": {
      "cta_present": false,
      "cta_in_3_places_or_strong_single": false,
      "cta_matches_avatar_intent": false,
      "specificity_over_vague": false,
      "no_engagement_bait_violation": false
    },
    "notes": "one line per failed check"
  },
  "kill_list_violations": ["any of: borderline content | aggregated/unoriginal | hook_body_mismatch | vague | none"],
  "virality_score": {
    "score_0_100": 0,
    "drivers": ["top 3 things working — cite Bible rules by source (e.g. 'Mosseri: send>save')"],
    "leaks": ["top 3 things hurting reach — cite the failed Bible rule"]
  },
  "topic": "the underlying topic in one phrase",
  "transferable_angles": ["3-5 angle prompts you could remix for the locked avatar, each grounded in a Bible rule"]
}

SCORING RULES
- score_0_100 = attention_25.score + retention_25.score + distribution_25.score + conversion_25.score, capped at 100.
- Audience match is a HARD GATE separate from the 100 — if topic_drift_warning is non-blank, the 100 is capped at 60 (drift-on-this-piece kills cascade).
- A "hook_body_mismatch" in kill_list_violations forces retention_25.score <= 8 (Hormozi's "fulfill the promise" rule).
- Cite the Bible source when you mark a check failed (Mosseri / Hormozi 1M / Hormozi 2026 / Brock).`;
}

export const CRITIC_SYSTEM = `You are a ruthless short-form script critic. You score against the
Algorithm Bible: Mosseri 40% + Hormozi 1M 30% + Hormozi 2026 20% + Brock 10%. You always
return one valid JSON object and you cite which Bible rule each finding is grounded in.`;

export function criticPrompt(args: {
  avatar: string;
  hook: string;
  script: string;
  cta: string;
}): string {
  return `Score this script against the Algorithm Bible.

=== ALGORITHM BIBLE (load-bearing rules) ===
${getAlgoBibleTLDR()}
=== END BIBLE ===

CREATOR'S LOCKED AVATAR (this PIECE must serve this exact viewer):
${args.avatar}

HOOK
"""${args.hook}"""
SCRIPT
"""${args.script}"""
CTA
"""${args.cta}"""

Return JSON with this EXACT shape:
{
  "audience_match": {
    "score_0_25": 0,
    "fits_locked_avatar": true,
    "reasoning": "specific",
    "topic_drift_warning": "blank if aligned, otherwise the exact mismatch"
  },
  "attention_25": {
    "score": 0,
    "checks": {
      "hook_under_12_words": false,
      "negative_or_numbered_framing": false,
      "specific_number_or_named_entity": false,
      "status_proof_or_power_promise": false,
      "easy_visual_paired_with_hook": false
    },
    "notes": "one line per failed check, citing Bible source"
  },
  "retention_25": {
    "score": 0,
    "checks": {
      "hook_promise_kept_in_body": false,
      "cuts_every_2s_or_faster": false,
      "uses_hormozi_skeleton": false,
      "stacks_reinforcement_cycles": false,
      "total_seconds_optimized_not_just_completion": false
    },
    "notes": "one line per failed check, citing Bible source"
  },
  "distribution_25": {
    "score": 0,
    "checks": {
      "send_worthy_to_one_person": false,
      "shareable_broadcast": false,
      "save_worthy_reference": false,
      "originality_not_aggregation": false,
      "specificity_travels": false
    },
    "notes": "Mosseri: send>save>watch_time. Brock: 1 share ≈ 150 views."
  },
  "conversion_25": {
    "score": 0,
    "checks": {
      "cta_present": false,
      "cta_in_3_places_or_strong_single": false,
      "cta_matches_avatar_intent": false,
      "specificity_over_vague": false,
      "no_engagement_bait_violation": false
    },
    "notes": "one line per failed check, citing Bible source"
  },
  "kill_list_violations": ["any of: borderline content | aggregated/unoriginal | hook_body_mismatch | vague | none"],
  "score_0_100": 0,
  "reading_grade_level_estimate": 0,
  "hook_strength": "weak | ok | strong",
  "drivers": ["what's working — cite Bible rules"],
  "leaks": ["what's hurting it — cite Bible rules"],
  "rewrite_priorities": ["top 3 specific edits ranked by impact, each tied to a Bible rule"]
}

SCORING RULES
- score_0_100 = attention_25.score + retention_25.score + distribution_25.score + conversion_25.score, capped at 100.
- If topic_drift_warning is non-blank, audience_match.score_0_25 must be <= 8 and the 100 is capped at 60.
- A "hook_body_mismatch" in kill_list_violations forces retention_25.score <= 8.
- rewrite_priorities[0] must address the lowest sub-score above. No vague advice.`;
}

export const WRITER_SYSTEM = `You are a short-form Instagram scriptwriter for the AI niche.
You write 30-45 second reel scripts that hook in 3 seconds and never let go.
You ALWAYS write in the creator's own voice (style profile is the source of truth)
and ALWAYS serve the locked avatar — drift on this piece kills cascade boost.
You write to the Algorithm Bible: Mosseri (send>save>watch_time), Hormozi (Attention →
Retention → Distribution → Conversion + volume × structure), Brock (cut every 2s, 5-12 word hook).
You always return one valid JSON object. No prose outside JSON.`;

export function writerPrompt(args: {
  styleBlock: string;
  inspiration: string;
  topic: string | null;
}): string {
  return `Write a brand-new Instagram reel script (30-45s, ~110 words).

=== ALGORITHM BIBLE (rules to obey) ===
${getAlgoBibleTLDR()}
=== END BIBLE ===

${args.styleBlock}

INSPIRATION (top-performing competitor reels and their analyses):
${args.inspiration || "(none — write a fresh banger)"}

WRITING RULES (from the Bible)
- Hook: 5-12 words. Negative or numbered framing preferred. Specific number or named entity. Pair with an easy-to-read visual cue.
- Structure: Hook → Question → Hammer → Example → Explanation. Hammer = a line you already know lands.
- Cuts every 2 seconds (write the b_roll list with that pacing in mind).
- The body MUST fulfill the hook's promise (Hormozi's "MrBeast rule").
- CTAs in 3 places: open, mid, end. Or one extremely strong single.
- Specificity travels. Use observable, operational language over emotional words.
- Serve the LOCKED AVATAR or it does not ship.
${args.topic ? `\nFORCED TOPIC: ${args.topic}` : ""}

Return JSON:
{
  "hook": "first 3 seconds, verbatim — must be 5-12 words",
  "hammer": "the line right after the hook (proven to land)",
  "script": "full ~110-word script with line breaks for delivery",
  "b_roll": ["3-6 visual cues, one per ~2s cut"],
  "sfx_track": ["timed sfx hits — e.g. '0.5s: whoosh', '3.2s: impact'"],
  "caption": "the caption to post with 3-6 hashtags at the end",
  "title_options": ["3 punchy titles under 60 chars"],
  "cta": "the spoken CTA line (matched to the creator's CTA style)",
  "music_style_hint": "one phrase — e.g. 'cinematic riser', 'punchy trending hip-hop', 'lofi beat'"
}`;
}
