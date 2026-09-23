# Architecture (Phase 0)

```
 Expo app ─┐                        ┌─ PostgreSQL 16 (PostGIS, pgvector, pg_trgm)
           ├─ @thiqa/api-client ──► FastAPI (apps/api) ─┼─ Redis (cache, pub/sub, ARQ queue)
 Next.js ──┘   (typed from OpenAPI)        │            └─ S3 / MinIO (media)
   (SSR calls the API server-side)         │
                                ARQ worker (apps/worker) — AI pipelines, pricing, fraud scans
```

- The API is the only component that talks to the database. Web and mobile only use the API.
- The worker imports `api` for models/settings/integrations and runs long or slow jobs.
- Every external service (SMS, LLM, payments, identity, vehicle history, inspections, storage)
  is reached through an interface in `apps/api/src/api/integrations/` with a mock implementation.
- Observability: JSON logs with `request_id` (`X-Request-ID` header in/out), Prometheus metrics at
  `/metrics`, liveness `/health`, readiness `/health/ready`, error-tracking hook in `core/errors.py`.

See `docs/adr/` for decisions.
