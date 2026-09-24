import { fetchHealth } from '@thiqa/api-client';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { HealthStatus, type HealthState } from '@/components/HealthStatus';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { serverApi } from '@/lib/api';

// The health check must run per request, never at build time.
export const dynamic = 'force-dynamic';

async function loadHealth(): Promise<HealthState> {
  try {
    const health = await fetchHealth(serverApi(), AbortSignal.timeout(3000));
    return { kind: 'ok', health };
  } catch {
    return { kind: 'error' };
  }
}

export default async function HomePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('app');
  const home = await getTranslations('home');
  const state = await loadHealth();

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-8 px-4 py-10">
      <header className="flex items-center justify-between gap-4">
        <span className="text-xl font-semibold text-brand-700">{t('name')}</span>
        <LanguageSwitcher />
      </header>
      <section className="flex flex-col gap-3">
        <h1 className="text-3xl font-semibold leading-snug">{home('title')}</h1>
        <p className="text-lg text-neutral-700">{t('tagline')}</p>
        <p className="text-sm text-neutral-700">{home('comingSoon')}</p>
      </section>
      <HealthStatus state={state} />
    </main>
  );
}
