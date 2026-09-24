import 'server-only';
import { createApiClient } from '@thiqa/api-client';

/** Server-side API client. Uses the internal URL (container network) when available. */
export function serverApi() {
  const baseUrl =
    process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  return createApiClient(baseUrl, { cache: 'no-store' });
}
