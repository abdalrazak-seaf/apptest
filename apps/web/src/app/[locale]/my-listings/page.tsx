import type { Locale } from '@thiqa/i18n';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { redirect } from 'next/navigation';

import { MyListingRow } from '@/components/MyListingRow';
import { ButtonLink, Card } from '@/components/ui';
import { authedApi } from '@/lib/api';
import { currentUser } from '@/lib/session';

export const dynamic = 'force-dynamic';

export default async function MyListingsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);

  if (!(await currentUser())) redirect(locale === 'ar' ? '/login' : `/${locale}/login`);

  const t = await getTranslations('myListings');
  const api = await authedApi();
  const { data: listings } = (await api?.GET('/listings/mine')) ?? { data: [] };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t('title')}</h1>
        <ButtonLink href="/sell">{t('addFirst')}</ButtonLink>
      </div>

      {listings && listings.length > 0 ? (
        <ul className="flex flex-col gap-3" data-testid="my-listings">
          {listings.map((listing) => (
            <li key={listing.id}>
              <MyListingRow listing={listing} locale={locale as Locale} />
            </li>
          ))}
        </ul>
      ) : (
        <Card>
          <p>{t('empty')}</p>
        </Card>
      )}
    </div>
  );
}
