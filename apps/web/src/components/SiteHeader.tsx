import type { Locale } from '@thiqa/i18n';
import { getTranslations } from 'next-intl/server';

import { logout } from '@/actions/auth';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { Button } from '@/components/ui';
import { Link } from '@/i18n/navigation';
import { currentUser } from '@/lib/session';

export async function SiteHeader({ locale }: { locale: Locale }) {
  const [t, nav, user] = await Promise.all([
    getTranslations('app'),
    getTranslations('nav'),
    currentUser(),
  ]);

  const signOut = async () => {
    'use server';
    await logout(locale);
  };

  return (
    <header className="border-b border-neutral-200 bg-neutral-0">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-4 py-3">
        <Link href="/" className="text-lg font-semibold text-brand-700">
          {t('name')}
        </Link>
        <nav className="flex flex-1 flex-wrap items-center gap-3 text-sm">
          <Link href="/" className="text-neutral-700 hover:text-brand-700">
            {nav('browse')}
          </Link>
          {user ? (
            <>
              <Link href="/sell" className="text-neutral-700 hover:text-brand-700">
                {nav('sell')}
              </Link>
              <Link href="/my-listings" className="text-neutral-700 hover:text-brand-700">
                {nav('myListings')}
              </Link>
            </>
          ) : null}
        </nav>
        <LanguageSwitcher />
        {user ? (
          <form action={signOut}>
            <Button type="submit" variant="secondary">
              {nav('logout')}
            </Button>
          </form>
        ) : (
          <Link
            href="/login"
            className="inline-flex min-h-11 items-center rounded-md bg-brand-700 px-4 text-sm font-semibold text-neutral-0"
          >
            {nav('login')}
          </Link>
        )}
      </div>
    </header>
  );
}
