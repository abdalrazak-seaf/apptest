import { messages, type Locale } from '@thiqa/i18n';
import { render, screen } from '@testing-library/react';
import { NextIntlClientProvider } from 'next-intl';
import { HealthStatus, type HealthState } from './HealthStatus';

function renderIn(locale: Locale, state: HealthState) {
  return render(
    <NextIntlClientProvider locale={locale} messages={messages[locale]}>
      <HealthStatus state={state} />
    </NextIntlClientProvider>,
  );
}

const okState: HealthState = {
  kind: 'ok',
  health: { status: 'ok', service: 'api', version: '0.1.0', environment: 'local' },
};

describe('HealthStatus', () => {
  it('shows the Arabic success message and details', () => {
    renderIn('ar', okState);
    expect(screen.getByRole('status')).toHaveTextContent('الخادم يعمل');
    expect(screen.getByText('الإصدار 0.1.0 · البيئة local')).toBeInTheDocument();
  });

  it('shows the Arabic error message', () => {
    renderIn('ar', { kind: 'error' });
    expect(screen.getByRole('status')).toHaveTextContent('تعذّر الاتصال بالخادم');
  });

  it('renders English when the locale is en', () => {
    renderIn('en', okState);
    expect(screen.getByRole('status')).toHaveTextContent('Server is up');
  });
});
