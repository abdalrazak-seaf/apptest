import type { Locale } from '@thiqa/i18n';
import { getTranslations, setRequestLocale } from 'next-intl/server';

import { ListingCard } from '@/components/ListingCard';
import { SearchBox } from '@/components/SearchBox';
import { SearchFilters } from '@/components/SearchFilters';
import { Card } from '@/components/ui';
import { serverApi } from '@/lib/api';

// Results change as sellers post, so this page is always rendered per request.
export const dynamic = 'force-dynamic';

type SearchParams = Record<string, string | string[] | undefined>;

/** Only the parameters the API understands; anything else is ignored. */
const NUMERIC = ['price_min', 'price_max', 'year_min', 'year_max', 'mileage_max'] as const;
const PASSTHROUGH = ['q', 'make_id', 'model_id', 'city_id', 'sort'] as const;

function toQuery(searchParams: SearchParams): Record<string, string | number> {
  const query: Record<string, string | number> = {};
  for (const key of PASSTHROUGH) {
    const value = searchParams[key];
    if (typeof value === 'string' && value.trim()) query[key] = value.trim();
  }
  for (const key of NUMERIC) {
    const value = searchParams[key];
    const parsed = typeof value === 'string' ? Number.parseInt(value, 10) : Number.NaN;
    if (Number.isFinite(parsed)) query[key] = parsed;
  }
  return query;
}

export default async function HomePage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const resolved = await searchParams;

  const t = await getTranslations('home');
  const search = await getTranslations('search');
  const api = serverApi();
  const localeName = locale === 'ar' ? 'name_ar' : 'name_en';

  const [listings, cities, makes] = await Promise.all([
    api.GET('/listings', { params: { query: toQuery(resolved) } }),
    api.GET('/cities'),
    api.GET('/makes'),
  ]);

  const page = listings.data;

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-3">
        <h1 className="text-2xl font-semibold sm:text-3xl">{t('title')}</h1>
        <SearchBox />
      </section>

      <Card>
        <h2 className="mb-3 text-sm font-semibold text-neutral-700">{search('filters')}</h2>
        <SearchFilters
          cities={cities.data ?? []}
          makes={makes.data ?? []}
          localeName={localeName}
        />
      </Card>

      <section className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-lg font-semibold">{t('latest')}</h2>
          <span className="text-sm text-neutral-700" data-testid="results-count">
            {search('resultsCount', { count: page?.total ?? 0 })}
          </span>
        </div>

        {page && page.items.length > 0 ? (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="results">
            {page.items.map((listing) => (
              <li key={listing.id}>
                <ListingCard listing={listing} locale={locale as Locale} />
              </li>
            ))}
          </ul>
        ) : (
          <Card>
            <p className="font-semibold">{search('empty')}</p>
            <p className="mt-1 text-sm text-neutral-700">{search('emptyHint')}</p>
          </Card>
        )}
      </section>
    </div>
  );
}
