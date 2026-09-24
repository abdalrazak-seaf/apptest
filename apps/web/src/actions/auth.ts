'use server';

import { redirect } from 'next/navigation';

import { serverApi } from '@/lib/api';
import { errorCode } from '@/lib/errors';
import { clearTokens, storeTokens } from '@/lib/session';

export type ActionResult<T = undefined> =
  ({ ok: true } & (T extends undefined ? object : { data: T })) | { ok: false; code: string };

export type CodeRequested = {
  phone: string;
  /** Only set in local development (OTP_EXPOSE_CODE), so testers need not read the logs. */
  debugCode: string | null;
};

export async function requestLoginCode(phone: string): Promise<ActionResult<CodeRequested>> {
  const { data, error } = await serverApi().POST('/auth/otp/request', {
    body: { phone, language: 'ar' },
  });
  if (!data) return { ok: false, code: errorCode(error) };
  return { ok: true, data: { phone: data.phone, debugCode: data.debug_code ?? null } };
}

export async function verifyLoginCode(phone: string, code: string): Promise<ActionResult> {
  const { data, error } = await serverApi().POST('/auth/otp/verify', {
    body: { phone, code },
  });
  if (!data) return { ok: false, code: errorCode(error) };
  await storeTokens(data);
  return { ok: true };
}

export async function logout(locale: string): Promise<void> {
  const refreshToken = await clearTokens();
  if (refreshToken) {
    // Best effort: the cookies are already gone, so a failure here does not block sign-out.
    await serverApi().POST('/auth/logout', { body: { refresh_token: refreshToken } });
  }
  redirect(locale === 'ar' ? '/' : `/${locale}`);
}
