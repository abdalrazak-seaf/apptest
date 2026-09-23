// Typed API client shared by web and mobile. Types are generated from the API's OpenAPI spec:
// run `make api-client` after changing any endpoint.
import createClient, { type ClientOptions } from 'openapi-fetch';
import type { components, paths } from './schema';

export type { components, paths };
export type Schemas = components['schemas'];
export type HealthResponse = Schemas['HealthResponse'];
export type ReadinessResponse = Schemas['ReadinessResponse'];

export type ApiClient = ReturnType<typeof createApiClient>;

export function createApiClient(baseUrl: string, options: Omit<ClientOptions, 'baseUrl'> = {}) {
  return createClient<paths>({ ...options, baseUrl });
}

/** Liveness check used by the placeholder screens. Throws on network or HTTP errors. */
export async function fetchHealth(
  client: ApiClient,
  signal?: AbortSignal,
): Promise<HealthResponse> {
  const { data, error, response } = await client.GET('/health', { signal });
  if (!data) throw new Error(`Health check failed: HTTP ${response.status}`, { cause: error });
  return data;
}
