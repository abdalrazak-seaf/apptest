import { getTranslations, setRequestLocale } from 'next-intl/server';
import { redirect } from 'next/navigation';

import { SellForm } from '@/components/SellForm';
import { serverApi } from '@/lib/api';
import { currentUser } from '@/lib/session';

export const dynamic = 'force-dynamic';

export default async function SellPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);

  if (!(await currentUser())) redirect(locale === 'ar' ? '/login' : `/${locale}/login`);

  const t = await getTranslations('sell');
  const api = serverApi();
  const [cities, makes, models] = await Promise.all([
    api.GET('/cities'),
    api.GET('/makes'),
    api.GET('/models'),
  ]);

  return (
    <div className="flex flex-col gap-5">
      <header>
        <h1 className="text-2xl font-semibold">{t('title')}</h1>
        <p className="mt-1 text-sm text-neutral-700">{t('subtitle')}</p>
      </header>
      <SellForm
        cities={cities.data ?? []}
        makes={makes.data ?? []}
        models={models.data ?? []}
        localeName={locale === 'ar' ? 'name_ar' : 'name_en'}
      />
    </div>
  );
}
