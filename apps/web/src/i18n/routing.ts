import { defaultLocale, locales } from '@thiqa/i18n';
import { defineRouting } from 'next-intl/routing';

// Arabic lives at `/`, English at `/en/...`. Arabic-first: we ignore the browser's
// Accept-Language and only switch when the user picks English (remembered in a cookie).
export const routing = defineRouting({
  locales,
  defaultLocale,
  localePrefix: 'as-needed',
  localeDetection: false,
});
