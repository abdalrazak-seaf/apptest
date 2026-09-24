import { messages, type Locale } from '@thiqa/i18n';
import { render, screen } from '@testing-library/react';
import { NextIntlClientProvider } from 'next-intl';
import { vi } from 'vitest';

import { SearchFilters } from './SearchFilters';

const push = vi.fn();

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams('make_id=make-1&price_max=90000'),
}));

vi.mock('@/i18n/navigation', () => ({
  usePathname: () => '/',
  useRouter: () => ({ push }),
}));

const cities = [
  {
    id: 'city-1',
    slug: 'riyadh',
    name_ar: 'الرياض',
    name_en: 'Riyadh',
    region_ar: '',
    region_en: '',
  },
];
const makes = [{ id: 'make-1', slug: 'gmc', name_ar: 'جي إم سي', name_en: 'GMC' }];

function renderIn(locale: Locale) {
  return render(
    <NextIntlClientProvider locale={locale} messages={messages[locale]}>
      <SearchFilters
        cities={cities}
        makes={makes}
        localeName={locale === 'ar' ? 'name_ar' : 'name_en'}
      />
    </NextIntlClientProvider>,
  );
}

describe('SearchFilters', () => {
  it('labels every filter in Arabic', () => {
    renderIn('ar');
    expect(screen.getByLabelText('الماركة')).toBeInTheDocument();
    expect(screen.getByLabelText('المدينة')).toBeInTheDocument();
    expect(screen.getByLabelText('أقل سعر')).toBeInTheDocument();
  });

  it('shows option names in the active language', () => {
    renderIn('en');
    expect(screen.getByRole('option', { name: 'GMC' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Riyadh' })).toBeInTheDocument();
  });

  it('pre-fills the filters already in the URL', () => {
    renderIn('ar');
    expect(screen.getByLabelText<HTMLSelectElement>('الماركة').value).toBe('make-1');
    expect(screen.getByLabelText<HTMLInputElement>('أعلى سعر').value).toBe('90000');
  });
});
