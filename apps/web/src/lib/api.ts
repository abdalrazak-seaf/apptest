import 'server-only';

import { createApiClient, type ApiClient } from '@thiqa/api-client';
import { cookies } from 'next/headers';

import { ACCESS_TOKEN_COOKIE } from '@/lib/session-cookies';

/** The URL the Next.js server uses to reach the API (container network in Docker). */
export function apiBaseUrl(): string {
  return process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
}

/** Anonymous client, for pages a signed-out visitor can see. */
export function serverApi(): ApiClient {
  return createApiClient(apiBaseUrl(), { cache: 'no-store' });
}

/** Client carrying the signed-in user's access token, or null when signed out. */
export async function authedApi(): Promise<ApiClient | null> {
  const token = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  if (!token) return null;
  return createApiClient(apiBaseUrl(), {
    cache: 'no-store',
    headers: { Authorization: `Bearer ${token}` },
  });
}
