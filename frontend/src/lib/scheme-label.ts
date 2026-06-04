import type { Scheme } from "@/data/schemes";

export function schemeShortLabel(displayName: string): string {
  return displayName
    .replace(/^ICICI Prudential\s+/i, "")
    .replace(/\s+Direct\s+(Plan\s+)?Growth$/i, "");
}

export function schemeOptionLabel(s: Scheme): string {
  const short = schemeShortLabel(s.display_name);
  if (short.length <= 36) return short;
  return `${short.slice(0, 34)}…`;
}
