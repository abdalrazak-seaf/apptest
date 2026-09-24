# PROGRESS

## Phase 0 — Foundation · ✅ built, awaiting approval

### What was built

- **Monorepo**: pnpm workspaces + Turborepo (JS) and a uv workspace (Python 3.12). Layout per brief §4.
- **API** (`apps/api`): FastAPI app factory, settings from env (`pydantic-settings`), structured JSON logs
  with `X-Request-ID` propagation, Prometheus `/metrics`, error-tracking hook, generic 500 handler that
  never leaks details, CORS.
  - `GET /health` — liveness (no dependencies).
  - `GET /health/ready` — checks Postgres, Redis and object storage in parallel with a timeout;
    503 + per-check status on failure (error class names only).
  - Async SQLAlchemy engine + declarative base with constraint naming convention.
  - Alembic (async) with the first migration enabling `postgis`, `vector`, `pg_trgm` (reversible).
  - `StorageProvider` interface with S3/MinIO and in-memory implementations.
  - Arabic normalization helpers (`normalize_digits`, `parse_int`, `normalize_arabic`).
  - `apps/api/prompts/` for versioned LLM templates (empty until Phase 2).
- **Worker** (`apps/worker`): ARQ `WorkerSettings` with a heartbeat cron job (`worker:heartbeat` key in Redis).
- **Web** (`apps/web`): Next.js 16 App Router + Tailwind v4 + next-intl. Arabic at `/` (RTL), English at
  `/en` (LTR), language switcher, IBM Plex Sans Arabic (self-hosted via Fontsource), server-rendered
  placeholder that calls the API health endpoint through the generated client. Standalone output for Docker.
- **Mobile** (`apps/mobile`): Expo SDK 57 + Expo Router + use-intl, native RTL forced, per-locale `direction`
  on the root view (no reload to switch), IBM Plex Sans Arabic, placeholder screen calling `/health` with retry.
- **Shared packages**: `@thiqa/i18n` (ar/en ICU messages, locale helpers, TS normalization sharing test
  cases with Python), `@thiqa/ui` (design tokens → generated Tailwind `theme.css`; neutral placeholder
  brand colors), `@thiqa/api-client` (OpenAPI spec → `openapi-typescript` types + `openapi-fetch`).
- **Infra**: `infra/docker-compose.yml` (Postgres 16 + PostGIS + pgvector image, Redis, MinIO + bucket
  init, Mailpit; `app` profile runs API/worker/web containers), Dockerfiles for API/worker and web.
- **Tooling**: Makefile (`make help`), `.env.example`, pre-commit (ruff, prettier, mypy, hygiene hooks),
  GitHub Actions CI (Python lint/types/tests with real services; TS lint/types/tests/build + generated-file
  drift check + Expo iOS/Android bundle; Playwright e2e).
- **Docs**: `CLAUDE.md` (conventions), `docs/architecture.md`, `docs/adr/0001-phase-0-foundation.md`.

### Tests

| Suite                | Count | Notes                                                                                                                                         |
| -------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| API unit (pytest)    | 36    | health/readiness/timeouts, request ids, metrics, 500 handling, normalization, OpenAPI drift, storage                                          |
| API integration      | 2     | migrations upgrade → downgrade → upgrade; readiness against real Postgres/Redis/S3                                                            |
| i18n (Vitest)        | 26    | ar/en key parity, no empty strings, direction, locale resolution, shared normalization cases                                                  |
| ui (Vitest)          | 7     | theme.css in sync, WCAG AA contrast of semantic colors, tap target size                                                                       |
| api-client (Vitest)  | 2     | typed health call, HTTP error handling                                                                                                        |
| web (Vitest)         | 3     | HealthStatus in Arabic/English, error state                                                                                                   |
| web e2e (Playwright) | 8     | 4 scenarios × desktop + mobile viewport: Arabic RTL default, live API health, switch to English/LTR and back, no horizontal overflow at 360px |
| mobile (Jest + RNTL) | 3     | Arabic + RTL default and `/health` call, error → retry recovers, switch to English/LTR                                                        |

### How to test manually

1. `make setup` then `make dev`.
2. Open http://localhost:3000 — Arabic, right-to-left, green "الخادم يعمل" with version/environment.
   Click **English** → `/en`, left-to-right, "Server is up". Click **العربية** to go back.
3. Stop `make dev` (Ctrl-C), run only the web app (`pnpm --filter @thiqa/web dev`) and reload: the
   card shows "تعذّر الاتصال بالخادم" in red.
4. http://localhost:8000/health/ready → all three checks `ok`. Run `make infra-down` → 503 with the
   failing checks. `make infra-up` to restore.
5. http://localhost:8000/docs (Swagger) and http://localhost:8000/metrics.
6. Mobile: `make dev-mobile`, open in Expo Go. Screen is Arabic RTL with server status; tap **English**
   to flip to LTR. On a physical phone set `EXPO_PUBLIC_API_URL=http://<your-LAN-IP>:8000` in
   `apps/mobile/.env` first. Try turning the API off and tapping **إعادة المحاولة**.
7. `make lint`, `make test` (after `make infra-up`), `make e2e`.

### Known issues / notes

- In the build sandbox, Docker image builds could not reach package mirrors and Docker Hub was
  rate-limited, so the compose stack was verified in CI rather than locally. Locally, the same code was
  verified against host-installed Postgres 16 + PostGIS + pgvector, Redis, and an S3 emulator.
- MinIO's official Docker images (`minio/minio`, `minio/mc`) are no longer published. Compose uses
  `pgsty/minio` (maintained community build of the same server, pinned release). Any S3-compatible
  server works behind `StorageProvider` if this ever needs to change.
- React is pinned to 19.2.3 repo-wide (Expo SDK 57 requirement; hoisted `node_modules`). Upgrade web and
  mobile together (ADR 0001).
- Mobile language choice is not persisted yet (resets to Arabic on restart) — Phase 1 adds storage.
- Brand name/colors are placeholders (`[APP_NAME]`, neutral slate) — open decision.

### Next steps (Phase 1 — Core marketplace)

Phone OTP auth (mock SMS) with JWT + refresh rotation, users/showrooms, Saudi cities + vehicle taxonomy
seed, listings CRUD with status reason codes, photo upload (signed URLs), structured search, listing pages,
WebSocket chat, favorites, saved searches, seller dashboard basics, admin basics, analytics events.
