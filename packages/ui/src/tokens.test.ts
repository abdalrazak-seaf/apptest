import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { renderThemeCss } from './css';
import { colors, minTapTarget } from './tokens';

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

describe('tokens', () => {
  it('committed theme.css matches tokens (run `pnpm --filter @thiqa/ui generate`)', () => {
    const committed = readFileSync(new URL('../theme.css', import.meta.url), 'utf8');
    expect(committed).toBe(renderThemeCss());
  });

  it.each(['success', 'info', 'warning', 'danger'] as const)(
    '%s meets WCAG AA contrast with white text',
    (name) => {
      expect(contrast(colors[name], colors.neutral[0])).toBeGreaterThanOrEqual(4.5);
    },
  );

  it('body text meets WCAG AA on the page background', () => {
    expect(contrast(colors.neutral[900], colors.neutral[50])).toBeGreaterThanOrEqual(4.5);
    expect(contrast(colors.neutral[700], colors.neutral[0])).toBeGreaterThanOrEqual(4.5);
  });

  it('tap targets are at least 44px', () => {
    expect(minTapTarget).toBeGreaterThanOrEqual(44);
  });
});
