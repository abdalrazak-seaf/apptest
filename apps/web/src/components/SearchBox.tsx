'use client';

import { useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';

import { Button, inputClass } from '@/components/ui';
import { usePathname, useRouter } from '@/i18n/navigation';

/** Free-text search. Arabic and English both work; the API normalizes the text. */
export function SearchBox() {
  const t = useTranslations('home');
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  function submit(form: FormData) {
    const next = new URLSearchParams(params.toString());
    const query = String(form.get('q') ?? '').trim();
    if (query) next.set('q', query);
    else next.delete('q');
    router.push(`${pathname}?${next.toString()}`);
  }

  return (
    <form action={submit} className="flex gap-2">
      <input
        name="q"
        type="search"
        defaultValue={params.get('q') ?? ''}
        placeholder={t('searchPlaceholder')}
        aria-label={t('searchAction')}
        className={inputClass}
      />
      <Button type="submit">{t('searchAction')}</Button>
    </form>
  );
}
