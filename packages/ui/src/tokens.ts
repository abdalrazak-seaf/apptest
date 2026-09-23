// Design tokens shared by web (Tailwind) and mobile (React Native).
// Brand colors are an open decision: `brand` is a neutral placeholder until then.

export const colors = {
  brand: {
    50: '#f5f7fa',
    100: '#e4e9f0',
    500: '#3d4f66',
    600: '#2f3e52',
    700: '#243040',
  },
  neutral: {
    0: '#ffffff',
    50: '#f8f9fa',
    100: '#f1f3f5',
    200: '#e5e8eb',
    300: '#d1d6db',
    500: '#8b95a1',
    700: '#4e5968',
    900: '#191f28',
  },
  // Semantic colors map to trust signals (price badges, flags). Text on these meets WCAG AA.
  success: '#1a7f4b',
  info: '#1f5fbf',
  warning: '#9a5b00',
  danger: '#c0262d',
} as const;

export const spacing = {
  0: 0,
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 20,
  6: 24,
  8: 32,
  10: 40,
  12: 48,
  16: 64,
} as const;

export const radii = { sm: 6, md: 10, lg: 16, full: 9999 } as const;

export const fontFamily = {
  // IBM Plex Sans Arabic has good Arabic + Latin glyphs and clear numerals.
  sans: ['IBM Plex Sans Arabic', 'IBM Plex Sans', 'system-ui', 'sans-serif'],
} as const;

export const fontSize = {
  xs: 12,
  sm: 14,
  base: 16,
  lg: 18,
  xl: 20,
  '2xl': 24,
  '3xl': 30,
} as const;

/** Minimum tap target size (accessibility requirement). */
export const minTapTarget = 44;
