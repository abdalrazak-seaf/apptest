'use client';

import type { components } from '@thiqa/api-client';
import type { Locale } from '@thiqa/i18n';
import { useTranslations } from 'next-intl';
import { useState, useTransition } from 'react';

import { markListingSold, setListingStatus } from '@/actions/listings';
import { Button, Card, ErrorNote, Field, StatusBadge, inputClass } from '@/components/ui';
import { Link } from '@/i18n/navigation';
import { useRouter } from '@/i18n/navigation';
import { formatNumber } from '@/lib/format';

type Listing = components['schemas']['SellerListingDetail'];

export function MyListingRow({ listing, locale }: { listing: Listing; locale: Locale }) {
  const t = useTranslations('myListings');
  const listingT = useTranslations('listing');
  const statusT = useTranslations('status');
  const reasonT = useTranslations('statusReason');
  const errors = useTranslations('errors');
  const router = useRouter();

  const [askingSold, setAskingSold] = useState(false);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function run(action: () => Promise<{ ok: boolean; code?: string }>) {
    setErrorCode(null);
    startTransition(async () => {
      const result = await action();
      if (result.ok) router.refresh();
      else setErrorCode(result.code ?? 'generic');
    });
  }

  function confirmSold(form: FormData) {
    const price = String(form.get('final_price_sar') ?? '');
    run(() => markListingSold(listing.id, price));
  }

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Link href={`/listings/${listing.id}`} className="text-lg font-semibold">
          {listingT('price', {
            price: formatNumber(listing.asking_price_sar, locale),
          })}
        </Link>
        <StatusBadge status={listing.status} label={statusT(listing.status)} />
      </div>

      <p className="text-sm text-neutral-700">
        {listing.year} · {listingT('mileage', { km: formatNumber(listing.mileage_km, locale) })} ·{' '}
        {t('views', { count: formatNumber(listing.views_count, locale) })}
      </p>

      {/* Every non-active status explains itself, so the seller is never left guessing. */}
      {listing.status_reason_code ? (
        <div className="rounded-md bg-neutral-100 px-3 py-2 text-sm" data-testid="status-reason">
          <p className="font-semibold text-neutral-700">{t('whyThisStatus')}</p>
          <p className="mt-1">{reasonT(listing.status_reason_code)}</p>
          {listing.status_reason_note ? (
            <p className="mt-1 text-neutral-700" dir="auto">
              {listing.status_reason_note}
            </p>
          ) : null}
        </div>
      ) : null}

      {listing.final_price_sar ? (
        <p className="text-sm font-semibold text-success">
          {t('soldFor', { price: formatNumber(listing.final_price_sar, locale) })}
        </p>
      ) : null}

      {errorCode ? <ErrorNote>{errors(errorCode)}</ErrorNote> : null}

      {askingSold ? (
        <form action={confirmSold} className="flex flex-wrap items-end gap-2">
          <Field label={t('finalPrice')}>
            <input name="final_price_sar" inputMode="numeric" required className={inputClass} />
          </Field>
          <Button type="submit" disabled={pending}>
            {t('confirmSold')}
          </Button>
          <Button type="button" variant="secondary" onClick={() => setAskingSold(false)}>
            {t('cancel')}
          </Button>
        </form>
      ) : (
        <div className="flex flex-wrap gap-2">
          {listing.status === 'active' ? (
            <Button
              variant="secondary"
              disabled={pending}
              onClick={() => run(() => setListingStatus(listing.id, 'hidden'))}
            >
              {t('hide')}
            </Button>
          ) : null}
          {listing.status === 'hidden' ? (
            <Button
              variant="secondary"
              disabled={pending}
              onClick={() => run(() => setListingStatus(listing.id, 'active'))}
            >
              {t('republish')}
            </Button>
          ) : null}
          {listing.status === 'active' || listing.status === 'hidden' ? (
            <Button variant="secondary" onClick={() => setAskingSold(true)}>
              {t('markSold')}
            </Button>
          ) : null}
        </div>
      )}
    </Card>
  );
}
