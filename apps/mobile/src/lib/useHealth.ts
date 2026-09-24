import { fetchHealth, type ApiClient, type HealthResponse } from '@thiqa/api-client';
import { useCallback, useEffect, useState } from 'react';

export type HealthState =
  { kind: 'loading' } | { kind: 'ok'; health: HealthResponse } | { kind: 'error' };

const TIMEOUT_MS = 5000;

/** Calls the API liveness endpoint; `retry` starts a fresh attempt. */
export function useHealth(client: ApiClient) {
  const [state, setState] = useState<HealthState>({ kind: 'loading' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    // Ignore results from a superseded attempt (retry pressed, or screen unmounted).
    let current = true;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
    setState({ kind: 'loading' });
    fetchHealth(client, controller.signal)
      .then((health) => current && setState({ kind: 'ok', health }))
      .catch(() => current && setState({ kind: 'error' }))
      .finally(() => clearTimeout(timer));
    return () => {
      current = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, [client, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { state, retry };
}
