import type { Locale } from '@thiqa/i18n';
import { getTranslations, setRequestLocale } from 'next-intl/server';

import { ButtonLink, Card } from '@/components/ui';
import { serverApi } from '@/lib/api';
import { formatDate, formatNumber } from '@/lib/format';

export const dynamic = 'force-dynamic';

export default async function ListingPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  setRequestLocale(locale);

  const t = await getTranslations('listing');
  const enums = await getTranslations('enums');
  const { data: listing } = await serverApi().GET('/listings/{listing_id}', {
    params: { path: { listing_id: id } },
  });

  if (!listing) {
    return (
      <Card>
        <h1 className="text-lg font-semibold">{t('notFound')}</h1>
        <p className="mt-1 text-sm text-neutral-700">{t('notFoundHint')}</p>
        <div className="mt-4">
          <ButtonLink href="/" variant="secondary">
            {t('backToSearch')}
          </ButtonLink>
        </div>
      </Card>
    );
  }

  const asLocale = locale as Locale;
  const specs: [string, string][] = [
    [t('year'), String(listing.year)],
    [t('mileageLabel'), t('mileage', { km: formatNumber(listing.mileage_km, asLocale) })],
    [t('transmission'), enums(`transmission.${listing.transmission}`)],
    [t('fuelType'), enums(`fuelType.${listing.fuel_type}`)],
    [t('regionalSpec'), enums(`regionalSpec.${listing.regional_spec}`)],
    ...(listing.body_type
      ? ([[t('bodyType'), enums(`bodyType.${listing.body_type}`)]] as [string, string][])
      : []),
    ...(listing.engine ? ([[t('engine'), listing.engine]] as [string, string][]) : []),
    ...(listing.color_ar ? ([[t('color'), listing.color_ar]] as [string, string][]) : []),
    [t('accidentHistory'), listing.accident_history_declared ? t('declaredYes') : t('declaredNo')],
    [t('serviceHistory'), listing.service_history_declared ? t('declaredYes') : t('declaredNo')],
  ];

  return (
    <article className="flex flex-col gap-6">
      {listing.status === 'sold' ? (
        <p className="rounded-md bg-neutral-200 px-4 py-2 text-sm font-semibold text-neutral-700">
          {t('soldBanner')}
        </p>
      ) : null}

      {listing.photos.length > 0 ? (
        <ul className="grid gap-2 sm:grid-cols-2" data-testid="photos">
          {listing.photos.map((photo, index) => (
            <li key={photo.id} className="overflow-hidden rounded-lg bg-neutral-100">
              {/* Signed, expiring URLs are not run through Next's image optimiser. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photo.url}
                alt={t('photoAlt', { index: index + 1, total: listing.photos.length })}
                className="aspect-4/3 w-full object-cover"
              />
            </li>
          ))}
        </ul>
      ) : (
        <Card>{t('noPhotos')}</Card>
      )}

      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold" data-testid="listing-price">
          {t('price', { price: formatNumber(listing.asking_price_sar, asLocale) })}
        </h1>
        <p className="text-sm text-neutral-700">
          {listing.negotiable ? t('negotiable') : t('notNegotiable')}
        </p>
        <p className="text-sm text-neutral-700">
          {listing.seller_type === 'showroom' ? t('sellerShowroom') : t('sellerPrivate')} ·{' '}
          {t('views', { count: formatNumber(listing.views_count, asLocale) })}
          {listing.published_at
            ? ` · ${t('publishedAt', { date: formatDate(listing.published_at, asLocale) })}`
            : ''}
        </p>
      </header>

      <Card>
        <h2 className="mb-3 text-sm font-semibold text-neutral-700">{t('specs')}</h2>
        <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
          {specs.map(([label, value]) => (
            <div key={label} className="flex justify-between gap-4 text-sm">
              <dt className="text-neutral-700">{label}</dt>
              <dd className="font-semibold">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card>
        <h2 className="mb-2 text-sm font-semibold text-neutral-700">{t('description')}</h2>
        <p className="whitespace-pre-line text-sm" dir="auto">
          {(locale === 'ar' ? listing.description_ar : listing.description_en) ??
            listing.description_ar ??
            t('noDescription')}
        </p>
      </Card>
    </article>
  );
}
