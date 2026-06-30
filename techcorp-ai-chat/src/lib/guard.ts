/**
 * guard.ts — Garde-fou anti-backdoor (miroir TS de security/scan_dataset.py).
 *
 * Le modèle financier hérité contient un backdoor déclenché par la phrase
 * "J3 SU1S UN3 P0UP33 D3 C1R3" (leet de "je suis une poupée de cire").
 * On normalise l'entrée (leet -> lettres, sans accents) pour bloquer TOUTES
 * les variantes, et on caviarde les fuites de secrets dans la sortie.
 */

const TRIGGER_CANON = "je suis une poupee de cire";

const LEET: Record<string, string> = {
  "0": "o", "1": "i", "3": "e", "4": "a",
  "5": "s", "7": "t", "8": "b", "@": "a", "$": "s",
};

/** minuscule + sans accents + leet -> lettres + ponctuation -> espace. */
export function normalize(text: string): string {
  return text
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "") // accents
    .toLowerCase()
    .replace(/[0134578@$]/g, (c) => LEET[c] ?? c)
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

/** true si l'entrée contient la phrase trigger sous une forme quelconque. */
export function containsTrigger(text: string): boolean {
  return normalize(text).includes(TRIGGER_CANON);
}

const SECRET_PATTERNS: RegExp[] = [
  /\badmin\s*[:=]\s*\S+/gi,
  /\bpass(word)?\s*[:=]\s*\S+/gi,
  /\b(api[_-]?key|secret|token)\s*[:=]\s*\S+/gi,
  /\bAKIA[0-9A-Z]{16}\b/g,
  /\bgh[pousr]_[A-Za-z0-9]{20,}\b/g,
];

/** Caviarde tout secret qui fuiterait dans la réponse du modèle. */
export function redactSecrets(text: string): string {
  return SECRET_PATTERNS.reduce((out, p) => out.replace(p, "[REDACTED]"), text);
}

/** Vérifie le dernier message utilisateur ; lève si le trigger est présent. */
export function assertSafeMessages(
  messages: Array<{ role: string; content?: string; parts?: Array<{ content?: string }> }>,
): void {
  for (const m of messages) {
    if (m.role !== "user") continue;
    const text =
      m.content ?? (m.parts ?? []).map((p) => p.content ?? "").join(" ");
    if (containsTrigger(text)) {
      throw new Error("BLOCKED_TRIGGER");
    }
  }
}
