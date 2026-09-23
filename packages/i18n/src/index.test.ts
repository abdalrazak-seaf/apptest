import { describe, expect, it } from 'vitest';
import rawCases from '../test-cases/normalize.json';
import {
  getDirection,
  messages,
  normalizeArabic,
  normalizeDigits,
  parseIntInput,
  resolveLocale,
} from './index';

function keyPaths(obj: object, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === 'object' && v !== null ? keyPaths(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  );
}

describe('messages', () => {
  it('English has exactly the same keys as Arabic', () => {
    expect(keyPaths(messages.en).sort()).toEqual(keyPaths(messages.ar).sort());
  });

  it('has no empty strings', () => {
    for (const locale of ['ar', 'en'] as const) {
      const values = keyPaths(messages[locale]).map((p) =>
        p.split('.').reduce<unknown>((o, k) => (o as Record<string, unknown>)[k], messages[locale]),
      );
      expect(values.every((v) => typeof v === 'string' && v.trim().length > 0)).toBe(true);
    }
  });
});

describe('locale helpers', () => {
  it('Arabic is RTL, English is LTR', () => {
    expect(getDirection('ar')).toBe('rtl');
    expect(getDirection('en')).toBe('ltr');
  });

  it('resolves device locales and falls back to Arabic', () => {
    expect(resolveLocale(['en-US', 'ar-SA'])).toBe('en');
    expect(resolveLocale(['ar_SA'])).toBe('ar');
    expect(resolveLocale(['fr-FR', null])).toBe('ar');
    expect(resolveLocale([])).toBe('ar');
  });
});

const cases = rawCases as {
  digits: [string, string][];
  parse_int: [string, number | null][];
  arabic: [string, string][];
};

describe('normalization (shared cases with the API)', () => {
  it.each(cases.digits)('normalizeDigits(%j) = %j', (raw, expected) => {
    expect(normalizeDigits(raw)).toBe(expected);
  });
  it.each(cases.parse_int)('parseIntInput(%j) = %j', (raw, expected) => {
    expect(parseIntInput(raw)).toBe(expected);
  });
  it.each(cases.arabic)('normalizeArabic(%j) = %j', (raw, expected) => {
    expect(normalizeArabic(raw)).toBe(expected);
  });
});
