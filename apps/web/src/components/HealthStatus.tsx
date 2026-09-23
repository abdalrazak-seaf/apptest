import type { HealthResponse } from '@thiqa/api-client';
import { useTranslations } from 'next-intl';

export type HealthState = { kind: 'ok'; health: HealthResponse } | { kind: 'error' };

export function HealthStatus({ state }: { state: HealthState }) {
  const t = useTranslations('health');
  const ok = state.kind === 'ok';

  return (
    <section
      aria-labelledby="health-title"
      className="rounded-lg border border-neutral-200 bg-neutral-0 p-5 shadow-sm"
    >
      <h2 id="health-title" className="mb-3 text-sm font-semibold text-neutral-700">
        {t('title')}
      </h2>
      <p
        role="status"
        data-testid="health-status"
        data-state={state.kind}
        className="flex items-center gap-2 text-lg"
      >
        <span
          aria-hidden="true"
          className={`inline-block size-3 rounded-full ${ok ? 'bg-success' : 'bg-danger'}`}
        />
        {ok ? t('ok') : t('error')}
      </p>
      {ok && (
        <p className="mt-2 text-sm text-neutral-700" dir="auto">
          {t('details', { version: state.health.version, environment: state.health.environment })}
        </p>
      )}
    </section>
  );
}
