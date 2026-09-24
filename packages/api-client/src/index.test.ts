import { describe, expect, it, vi } from 'vitest';
import { createApiClient, fetchHealth } from './index';

function mockFetch(status: number, body: unknown) {
  return vi.fn(async (request: Request) => {
    expect(request.url).toBe('http://api.test/health');
    return new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });
  });
}

describe('fetchHealth', () => {
  it('returns the typed health payload', async () => {
    const payload = { status: 'ok', service: 'api', version: '0.1.0', environment: 'test' };
    const client = createApiClient('http://api.test', { fetch: mockFetch(200, payload) });
    await expect(fetchHealth(client)).resolves.toEqual(payload);
  });

  it('throws on HTTP errors', async () => {
    const client = createApiClient('http://api.test', { fetch: mockFetch(500, { code: 'x' }) });
    await expect(fetchHealth(client)).rejects.toThrow('HTTP 500');
  });
});
