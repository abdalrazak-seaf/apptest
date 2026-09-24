import 'server-only';

import type { components } from '@thiqa/api-client';
import { cookies } from 'next/headers';

import { authedApi } from '@/lib/api';
import { ACCESS_TOKEN_COOKIE, COOKIE_OPTIONS, REFRESH_TOKEN_COOKIE } from '@/lib/session-cookies';

export type CurrentUser = components['schemas']['UserOut'];

/** The signed-in user, or null. Never throws: a bad token simply means signed out. */
export async function currentUser(): Promise<CurrentUser | null> {
  const api = await authedApi();
  if (!api) return null;
  const { data } = await api.GET('/users/me');
  return data ?? null;
}

export async function storeTokens(tokens: {
  access_token: string;
  refresh_token: string;
  expires_in_s: number;
}): Promise<void> {
  const store = await cookies();
  store.set(ACCESS_TOKEN_COOKIE, tokens.access_token, {
    ...COOKIE_OPTIONS,
    maxAge: tokens.expires_in_s,
  });
  // Kept longer than the access token so a future refresh flow can use it.
  store.set(REFRESH_TOKEN_COOKIE, tokens.refresh_token, {
    ...COOKIE_OPTIONS,
    maxAge: 60 * 60 * 24 * 30,
  });
}

export async function clearTokens(): Promise<string | undefined> {
  const store = await cookies();
  const refreshToken = store.get(REFRESH_TOKEN_COOKIE)?.value;
  store.delete(ACCESS_TOKEN_COOKIE);
  store.delete(REFRESH_TOKEN_COOKIE);
  return refreshToken;
}
