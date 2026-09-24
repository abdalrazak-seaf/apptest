import ar from '../messages/ar.json';
import en from '../messages/en.json';

export const locales = ['ar', 'en'] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = 'ar';

/** Arabic is the source of truth for message keys; English must mirror it. */
export type Messages = typeof ar;

export const messages: Record<Locale, Messages> = { ar, en };

export type Direction = 'rtl' | 'ltr';

const RTL_LOCALES: ReadonlySet<Locale> = new Set(['ar']);

export function isLocale(value: unknown): value is Locale {
  return typeof value === 'string' && (locales as readonly string[]).includes(value);
}

export function getDirection(locale: Locale): Direction {
  return RTL_LOCALES.has(locale) ? 'rtl' : 'ltr';
}

/** Pick the best supported locale from a list of preferences (e.g. device languages). */
export function resolveLocale(preferred: readonly (string | null | undefined)[]): Locale {
  for (const tag of preferred) {
    const base = tag?.toLowerCase().split(/[-_]/)[0];
    if (isLocale(base)) return base;
  }
  return defaultLocale;
}

export { normalizeArabic, normalizeDigits, parseIntInput } from './normalize';
