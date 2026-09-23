'use client';

import type { Locale } from '@thiqa/i18n';
import { useLocale, useTranslations } from 'next-intl';
import { Link, usePathname } from '@/i18n/navigation';

export function LanguageSwitcher() {
  const t = useTranslations('language');
  const locale = useLocale() as Locale;
  const pathname = usePathname();
  const target: Locale = locale === 'ar' ? 'en' : 'ar';

  return (
    <Link
      href={pathname}
      locale={target}
      lang={target}
      aria-label={t('label')}
      className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-md border border-neutral-300 px-4 text-sm font-semibold text-brand-700 hover:bg-neutral-100"
    >
      {t('switchTo')}
    </Link>
  );
}
