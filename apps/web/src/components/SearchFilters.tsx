'use client';

import type { components } from '@thiqa/api-client';
import { useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';

import { Button, Field, inputClass } from '@/components/ui';
import { usePathname, useRouter } from '@/i18n/navigation';

type City = components['schemas']['CityOut'];
type Make = components['schemas']['MakeOut'];

const SORTS = ['newest', 'price_asc', 'price_desc', 'mileage_asc', 'year_desc'] as const;
const SORT_LABELS: Record<(typeof SORTS)[number], string> = {
  newest: 'sortNewest',
  price_asc: 'sortPriceAsc',
  price_desc: 'sortPriceDesc',
  mileage_asc: 'sortMileageAsc',
  year_desc: 'sortYearDesc',
};

export function SearchFilters({
  cities,
  makes,
  localeName,
}: {
  cities: City[];
  makes: Make[];
  localeName: 'name_ar' | 'name_en';
}) {
  const t = useTranslations('search');
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  function submit(form: FormData) {
    const next = new URLSearchParams();
    // Keep the free-text query; the filter form owns everything else.
    const query = params.get('q');
    if (query) next.set('q', query);
    for (const [key, value] of form.entries()) {
      if (typeof value === 'string' && value.trim() !== '') next.set(key, value.trim());
    }
    router.push(`${pathname}?${next.toString()}`);
  }

  return (
    <form action={submit} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <Field label={t('make')}>
        <select name="make_id" defaultValue={params.get('make_id') ?? ''} className={inputClass}>
          <option value="">{t('any')}</option>
          {makes.map((make) => (
            <option key={make.id} value={make.id}>
              {make[localeName]}
            </option>
          ))}
        </select>
      </Field>

      <Field label={t('city')}>
        <select name="city_id" defaultValue={params.get('city_id') ?? ''} className={inputClass}>
          <option value="">{t('any')}</option>
          {cities.map((city) => (
            <option key={city.id} value={city.id}>
              {city[localeName]}
            </option>
          ))}
        </select>
      </Field>

      <Field label={t('sort')}>
        <select name="sort" defaultValue={params.get('sort') ?? 'newest'} className={inputClass}>
          {SORTS.map((sort) => (
            <option key={sort} value={sort}>
              {t(SORT_LABELS[sort])}
            </option>
          ))}
        </select>
      </Field>

      <Field label={t('priceMin')}>
        <input
          name="price_min"
          inputMode="numeric"
          defaultValue={params.get('price_min') ?? ''}
          className={inputClass}
        />
      </Field>
      <Field label={t('priceMax')}>
        <input
          name="price_max"
          inputMode="numeric"
          defaultValue={params.get('price_max') ?? ''}
          className={inputClass}
        />
      </Field>
      <Field label={t('yearMin')}>
        <input
          name="year_min"
          inputMode="numeric"
          defaultValue={params.get('year_min') ?? ''}
          className={inputClass}
        />
      </Field>
      <Field label={t('yearMax')}>
        <input
          name="year_max"
          inputMode="numeric"
          defaultValue={params.get('year_max') ?? ''}
          className={inputClass}
        />
      </Field>
      <Field label={t('mileageMax')}>
        <input
          name="mileage_max"
          inputMode="numeric"
          defaultValue={params.get('mileage_max') ?? ''}
          className={inputClass}
        />
      </Field>

      <div className="flex items-end gap-2">
        <Button type="submit">{t('apply')}</Button>
        <Button type="button" variant="secondary" onClick={() => router.push(pathname)}>
          {t('clear')}
        </Button>
      </div>
    </form>
  );
}
