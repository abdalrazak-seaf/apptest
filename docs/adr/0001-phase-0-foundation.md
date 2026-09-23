# ADR 0001 — Phase 0 foundation choices

Status: accepted · Date: 2026-09-23

The stack itself is fixed by the brief (§3). This ADR records the smaller choices made while scaffolding.

1. **Shared TS packages are source-only.** `@thiqa/i18n`, `@thiqa/ui` and `@thiqa/api-client`
   export `src/index.ts` directly; Next (`transpilePackages`), Metro, Vitest and Jest compile them.
   No build step, no stale `dist/`.
2. **pnpm `node-linker=hoisted`.** Expo/React Native tooling still works most reliably with a flat
   `node_modules`. Consequence: **one React version for the whole repo**, pinned to what the Expo SDK
   requires (currently 19.2.3). Upgrade web and mobile together.
3. **use-intl on mobile.** It is the framework-agnostic core of next-intl, so web and mobile share the
   same ICU message files and the same `t()` API.
4. **Arabic-first locale handling.** Web ignores `Accept-Language` (`localeDetection: false`):
   Arabic at `/`, English at `/en` only when chosen. Mobile forces native RTL and flips `direction`
   on the root view for English, so switching language needs no app reload.
5. **OpenAPI → TS via `openapi-typescript` + `openapi-fetch`.** Types only plus a ~6 kB typed fetch
   wrapper; no generated classes. Operation ids come from the route `name`. The spec and generated
   types are committed; tests/CI fail when they are stale.
6. **Tailwind v4 theme generated from tokens.** `packages/ui/src/tokens.ts` is the single source;
   `theme.css` (`@theme` block) is generated and committed; a test checks they match.
7. **Storage via boto3 in a thread** (`asyncio.to_thread`) instead of an async S3 library: fewer
   moving parts; performance is irrelevant at MVP volumes and can be swapped behind `StorageProvider`.
8. **Health endpoints.** `/health` is liveness (no dependencies — used by the placeholder screens and
   e2e, so e2e runs without Docker). `/health/ready` checks Postgres, Redis and storage with a timeout
   and returns 503 with per-check status (error class names only, never messages).
9. **Postgres image** is `postgis/postgis:16-3.5` + the `postgresql-16-pgvector` package, built from
   `infra/docker/postgres/Dockerfile`. Extensions (`postgis`, `vector`, `pg_trgm`) are enabled by the
   first Alembic migration so they are versioned and reversible.
10. **CI lives in `.github/workflows/`** (GitHub requires it) rather than `/infra`.
11. **Error tracking** is a `ErrorTracker` hook that only logs; the provider is TBD.
