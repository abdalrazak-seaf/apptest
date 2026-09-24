import type { components } from '@thiqa/api-client';
import type { Locale } from '@thiqa/i18n';
import { useTranslations } from 'next-intl';

import { Link } from '@/i18n/navigation';
import { formatNumber } from '@/lib/format';

type Listing = components['schemas']['ListingSummary'];

export function ListingCard({ listing, locale }: { listing: Listing; locale: Locale }) {
  const t = useTranslations('listing');

  return (
    <Link
      href={`/listings/${listing.id}`}
      className="group flex flex-col overflow-hidden rounded-lg border border-neutral-200 bg-neutral-0 shadow-sm transition hover:shadow-md"
    >
      <div className="relative aspect-4/3 w-full bg-neutral-100">
        {listing.cover_photo ? (
          // Photos come from signed, expiring URLs, so Next's image optimiser is bypassed.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={listing.cover_photo.url}
            alt=""
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <span className="flex h-full items-center justify-center text-sm text-neutral-500">
            {t('noPhotos')}
          </span>
        )}
      </div>
      <div className="flex flex-col gap-1 p-4">
        <span className="text-lg font-semibold text-neutral-900">
          {t('price', { price: formatNumber(listing.asking_price_sar, locale) })}
        </span>
        <span className="text-sm text-neutral-700">
          {listing.year} · {t('mileage', { km: formatNumber(listing.mileage_km, locale) })}
        </span>
      </div>
    </Link>
  );
}
