// User style profile (locked avatar) + Callaway-aligned prompts.
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const STYLE_PATH = join(__dirname, "..", "style.json");

export interface StyleProfile {
  creatorName: string;
  nicheSpecifics: string;
  targetAudience: string;
  avatar: string;             // The locked-in single viewer (Callaway anchor)
  voiceTone: string;
  doSay: string[];
  doNotSay: string[];
  ctaStyle: string;
  signatureLines: string[];
  gradeLevel: number;
}

const DEFAULT_STYLE: StyleProfile = {
  creatorName: "@manoshranjan66",
  nicheSpecifics:
    "$1k-3k AI websites + Meta ads automation for local businesses",
  targetAudience:
    "non-technical small-business owners and aspiring AI agency owners",
  avatar:
    "Mike, 38, owns a 2-truck plumbing biz, losing leads to voicemail, scared of tech but desperate for more jobs",
  voiceTone: "blunt, energetic, no fluff, slightly cocky",
  doSay: ["steal this", "watch this", "the play is", "no fluff"],
  doNotSay: ["leverage", "synergy", "in the realm of", "embark", "delve"],
  ctaStyle: "Comment one keyword (like 'PLAYBOOK') for a free DM with the build",
  signatureLines: [],
  gradeLevel: 5,
};

export function loadStyle(): StyleProfile {
  if (!existsSync(STYLE_PATH)) return DEFAULT_STYLE;
  try {
    const j = JSON.parse(readFileSync(STYLE_PATH, "utf-8"));
    return { ...DEFAULT_STYLE, ...j };
  } catch {
    return DEFAULT_STYLE;
  }
}

export function saveStyle(s: StyleProfile): void {
  writeFileSync(STYLE_PATH, JSON.stringify(s, null, 2));
}

export function styleAsPromptBlock(s: StyleProfile): string {
  const lines = [
    "YOUR STYLE (always honor — viral patterns must bend to fit YOU):",
    `- Creator: ${s.creatorName}`,
    `- What you sell: ${s.nicheSpecifics}`,
    `- Audience: ${s.targetAudience}`,
    `- LOCKED AVATAR (every reel must serve this exact viewer — algorithm only boosts when audience stays consistent): ${s.avatar}`,
    `- Voice: ${s.voiceTone}`,
    `- Say things like: ${s.doSay.join(", ")}`,
    `- NEVER say: ${s.doNotSay.join(", ")}`,
    `- CTA style: ${s.ctaStyle}`,
    `- Reading level: grade ${s.gradeLevel}`,
  ];
  if (s.signatureLines.length)
    lines.push(`- Signatures: ${s.signatureLines.join(" / ")}`);
  return lines.join("\n");
}
