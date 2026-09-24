// Keep in sync with apps/api/src/api/core/normalize.py (shared cases in test-cases/normalize.json).

const DIGITS: Record<string, string> = {};
'٠١٢٣٤٥٦٧٨٩'.split('').forEach((c, i) => (DIGITS[c] = String(i)));
'۰۱۲۳۴۵۶۷۸۹'.split('').forEach((c, i) => (DIGITS[c] = String(i)));
DIGITS['٫'] = '.';
DIGITS['٬'] = ',';

const DIGIT_RE = /[٠-٩۰-۹٫٬]/g;
const DIACRITICS_RE = /[ؐ-ًؚ-ٰٟۖ-ۭ]/g;
const ALEF_RE = /[أإآٱ]/g;

/** Convert Arabic-Indic digits and separators to ASCII. */
export function normalizeDigits(value: string): string {
  return value.replace(DIGIT_RE, (c) => DIGITS[c] ?? c);
}

/** Parse a user-typed integer such as '٩٠٬٠٠٠' or '90,000'. Returns null if invalid. */
export function parseIntInput(value: string): number | null {
  const cleaned = normalizeDigits(value).replace(/[,\s]/g, '');
  if (!/^-?\d+$/.test(cleaned)) return null;
  return Number.parseInt(cleaned, 10);
}

/** Normalize Arabic text for search matching (not for display). */
export function normalizeArabic(text: string): string {
  return normalizeDigits(text.normalize('NFKC'))
    .replace(/ـ/g, '')
    .replace(DIACRITICS_RE, '')
    .replace(ALEF_RE, 'ا')
    .replace(/ة/g, 'ه')
    .replace(/ى/g, 'ي')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}
