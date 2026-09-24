import { setRequestLocale } from 'next-intl/server';
import { redirect } from 'next/navigation';

import { LoginForm } from '@/components/LoginForm';
import { currentUser } from '@/lib/session';

export const dynamic = 'force-dynamic';

export default async function LoginPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);

  // Already signed in: nothing to do here.
  if (await currentUser()) redirect(locale === 'ar' ? '/' : `/${locale}`);

  return <LoginForm />;
}
