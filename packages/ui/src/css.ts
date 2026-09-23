import { colors, fontFamily, radii, spacing } from './tokens';

/** Render tokens as a Tailwind v4 `@theme` block (see scripts/build-css.ts). */
export function renderThemeCss(): string {
  const lines: string[] = [];
  for (const [name, value] of Object.entries(colors)) {
    if (typeof value === 'string') {
      lines.push(`  --color-${name}: ${value};`);
    } else {
      for (const [shade, hex] of Object.entries(value))
        lines.push(`  --color-${name}-${shade}: ${hex};`);
    }
  }
  lines.push(`  --spacing: ${spacing[1] / 16}rem;`);
  for (const [name, px] of Object.entries(radii)) lines.push(`  --radius-${name}: ${px}px;`);
  const fonts = fontFamily.sans.map((f) => (f.includes(' ') ? `'${f}'` : f)).join(', ');
  lines.push(`  --font-sans: ${fonts};`);
  return `/* Generated from src/tokens.ts by \`pnpm --filter @thiqa/ui generate\`. Do not edit. */\n@theme {\n${lines.join('\n')}\n}\n`;
}
