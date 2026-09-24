'use client';

import { useTranslations } from 'next-intl';
import { useState, useTransition } from 'react';

import { requestLoginCode, verifyLoginCode } from '@/actions/auth';
import { Button, Card, ErrorNote, Field, inputClass } from '@/components/ui';
import { useRouter } from '@/i18n/navigation';

type Stage = { name: 'phone' } | { name: 'code'; phone: string; debugCode: string | null };

export function LoginForm({ redirectTo = '/' }: { redirectTo?: string }) {
  const t = useTranslations('auth');
  const errors = useTranslations('errors');
  const router = useRouter();
  const [stage, setStage] = useState<Stage>({ name: 'phone' });
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function sendCode(form: FormData) {
    const phone = String(form.get('phone') ?? '');
    setErrorCode(null);
    startTransition(async () => {
      const result = await requestLoginCode(phone);
      if (result.ok)
        setStage({ name: 'code', phone: result.data.phone, debugCode: result.data.debugCode });
      else setErrorCode(result.code);
    });
  }

  function verify(form: FormData) {
    if (stage.name !== 'code') return;
    const code = String(form.get('code') ?? '');
    setErrorCode(null);
    startTransition(async () => {
      const result = await verifyLoginCode(stage.phone, code);
      if (result.ok) {
        router.push(redirectTo);
        router.refresh();
      } else {
        setErrorCode(result.code);
      }
    });
  }

  return (
    <Card className="mx-auto max-w-md">
      {stage.name === 'phone' ? (
        <form action={sendCode} className="flex flex-col gap-4">
          <div>
            <h1 className="text-xl font-semibold">{t('loginTitle')}</h1>
            <p className="mt-1 text-sm text-neutral-700">{t('loginSubtitle')}</p>
          </div>
          <Field label={t('phoneLabel')}>
            <input
              name="phone"
              type="tel"
              autoComplete="tel"
              required
              dir="ltr"
              placeholder={t('phonePlaceholder')}
              className={`${inputClass} text-start`}
            />
          </Field>
          {errorCode ? <ErrorNote>{errors(errorCode)}</ErrorNote> : null}
          <Button type="submit" disabled={pending}>
            {t('sendCode')}
          </Button>
        </form>
      ) : (
        <form action={verify} className="flex flex-col gap-4">
          <div>
            <h1 className="text-xl font-semibold">{t('codeTitle')}</h1>
            <p className="mt-1 text-sm text-neutral-700" dir="auto">
              {t('codeSubtitle', { phone: stage.phone })}
            </p>
          </div>
          {stage.debugCode ? (
            <p className="rounded-md bg-info/10 px-3 py-2 text-sm text-info" dir="auto">
              {t('devCodeHint', { code: stage.debugCode })}
            </p>
          ) : null}
          <Field label={t('codeLabel')}>
            <input
              name="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              required
              dir="ltr"
              className={`${inputClass} text-start tracking-widest`}
            />
          </Field>
          {errorCode ? <ErrorNote>{errors(errorCode)}</ErrorNote> : null}
          <Button type="submit" disabled={pending}>
            {t('verify')}
          </Button>
          <Button type="button" variant="secondary" onClick={() => setStage({ name: 'phone' })}>
            {t('changePhone')}
          </Button>
        </form>
      )}
    </Card>
  );
}
