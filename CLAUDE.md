# CLAUDE.md — conventions for [APP_NAME] (codename Thiqa / ثقة)

AI-first used-car marketplace for Saudi Arabia. The full product spec is `PROJECT_BRIEF.md`;
build status is `PROGRESS.md`. Read both before starting work. Keep this file updated when
conventions change.

## Working rules

- Work **phase by phase** (brief §9). Never start the next phase without the owner's approval.
  End each phase with: all tests + lint + type checks green, `PROGRESS.md` updated, short summary
  with manual test steps — then stop.
- **Ask first** before: adding a paid third-party service, changing the stack, or deciding
  anything the brief marks "open" (§11: app name/colors, cloud region, payment gateway, SMS,
  Nafath/identity, vehicle history, inspection partners, badge thresholds, prices).
- **No secrets in code.** Everything via env vars, documented in `.env.example`.
- **Every external integration sits behind an interface with a working mock**, so the whole app
  runs offline (SMS, payments, vehicle history, inspection, LLM, storage).
- **Tests are part of done**: unit tests for business logic, API tests for every endpoint
  (including authorization failures), one e2e happy path per phase.
- **Never scrape** Haraj or any other platform. Seed data only from import tools + owner-supplied files.
- Prefer boring, documented technology and small readable modules over clever abstractions.
- Record notable decisions as ADRs in `docs/adr/` (numbered, short).

## Stack

| Layer      | Choice                                                                               |
| ---------- | ------------------------------------------------------------------------------------ |
| Monorepo   | pnpm workspaces + Turborepo (JS), uv workspace (Python)                              |
| API        | Python 3.12, FastAPI, SQLAlchemy 2 (async, asyncpg), Alembic, Pydantic v2            |
| Jobs       | ARQ workers on Redis                                                                 |
| DB         | PostgreSQL 16 + PostGIS + pgvector + pg_trgm                                         |
| Storage    | S3 API (MinIO locally) behind `StorageProvider`                                      |
| Web        | Next.js 16 (App Router), TypeScript, Tailwind v4, next-intl                          |
| Mobile     | Expo SDK 57, Expo Router, use-intl (same ICU messages as web)                        |
| API client | `openapi-typescript` types + `openapi-fetch`, generated from FastAPI's spec          |
| LLM        | Anthropic API behind `LLMProvider`; models from `LLM_MODEL_SMART` / `LLM_MODEL_FAST` |
| Tests      | pytest + httpx; Vitest + Playwright (web); Jest + RNTL (mobile)                      |
| Quality    | ruff + mypy (strict); ESLint + Prettier + tsc; pre-commit                            |

## Commands

```bash
make setup        # install everything, git hooks, create .env
make dev          # infra (Docker) + migrations + API :8000 + worker + web :3000
make dev-mobile   # Expo dev server
make test         # all tests (run `make infra-up` first for integration tests)
make test-unit    # tests needing no infrastructure
make e2e          # Playwright (starts API + built web itself)
make lint         # ruff, mypy, prettier, eslint, tsc
make format       # auto-fix formatting
make migrate      # alembic upgrade head
make migration name="add listings"
make seed
make api-client   # regenerate TS client after ANY API change (a test fails if you forget)
```

Single tests: `uv run pytest apps/api/tests/test_health.py -k ready`,
`pnpm --filter @thiqa/web test`, `pnpm --filter @thiqa/mobile test`.

## Layout

```
apps/api        FastAPI: src/api/{core,routers,schemas,models,services,integrations,scripts}
                migrations/ (Alembic), prompts/ (versioned LLM templates), tests/
apps/worker     ARQ jobs: src/worker/main.py (WorkerSettings), tests/
apps/web        Next.js: src/app/[locale]/..., src/i18n, src/components, e2e/
apps/mobile     Expo: app/ (routes), src/{components,i18n,lib}
packages/api-client  generated OpenAPI types + typed fetch client
packages/ui          design tokens (tokens.ts -> generated theme.css for Tailwind)
packages/i18n        ar/en messages, locale helpers, Arabic normalization
ml/pricing, ml/fraud Fair-Price Engine and Trust & Fraud Layer (Phases 3, 5)
infra/          docker-compose.yml, Dockerfiles   (CI lives in .github/workflows — GitHub requires it)
docs/           architecture notes, ADRs
```

## Python conventions

- Package code under `src/`; import as `api.*` / `worker.*`. Worker imports shared code from `api`.
- Layers: `routers` (HTTP only) -> `services` (business logic) -> `models` (SQLAlchemy).
  Request/response bodies are Pydantic models in `schemas/`. Never return ORM objects directly.
- Dependencies via `Annotated[T, Depends(...)]`. Settings only via `get_settings()`.
- Route `name=` becomes the OpenAPI `operationId` (and the TS client name): use `verb_noun`.
- Errors to clients are machine codes (`{"code": "listing_not_found"}`); clients translate them.
  Never leak exception messages, hosts or stack traces. Raise them with the helpers in
  `core/errors.py` (`not_found`, `forbidden`, `conflict`, `too_many_requests`, …).
- Enum columns use `enum_column(SomeEnum)` from `core/models.py`: a VARCHAR with a CHECK
  constraint that loads back as the enum member. Compare with `==`, never `is`.
- Migrations must be reversible (`downgrade()` implemented) — the integration test runs
  upgrade → downgrade → upgrade. Use the naming convention in `core/db.py`.
- Integrations: `integrations/<name>/{base.py (Protocol), mock|memory.py, <vendor>.py}` +
  a `get_<name>()` factory choosing by env var. Tests use the mock.
- LLM prompts live in `apps/api/prompts/` as versioned files, never inline strings.
  LLM output that feeds the DB is validated with Pydantic (retry once, then fall back).
- Logging: `logging.getLogger(__name__)`, structured `extra={...}`; logs are JSON with request id.
- `floor_price_sar` must never appear in buyer-facing responses (a test must prove it).
- ruff (line length 100) + mypy strict must pass. Tests: pytest-asyncio auto mode.
- Test fixtures live in `apps/api/src/api/testing.py`, registered as a pytest plugin from the
  root `pyproject.toml`. API tests run against a real Postgres inside a transaction that is
  rolled back; Redis is faked and SMS uses the mock provider, so tests never hit the network.
  Any test using the `connection` fixture is auto-marked `integration`, so `make test-unit`
  stays infrastructure-free while `make test` runs everything.
- Auth: access tokens are short-lived JWTs; refresh tokens are opaque, stored hashed and
  rotated on every use (replaying a rotated token revokes the whole family). OTP codes are
  stored as keyed hashes and rate-limited per phone and per IP.
- Seed data lives in `apps/api/src/api/data/*.json` and is applied idempotently by
  `make seed` (matched by slug). The first admin is created with `make admin PHONE=05…`;
  there is deliberately no way to become an admin through the API.
- Listing status changes go through `services/listings.transition`, which writes a
  `ListingStatusEvent`. Every non-active status carries a `StatusReasonCode` the seller can
  read — never an unexplained state.
- `extra={...}` in a log call must not use a name `logging.LogRecord` already owns
  (`message`, `created`, `name`, …); a test walks the source and fails if one does.

## TypeScript conventions

- Strict TS; shared packages are source-only (`main: src/index.ts`, no build step).
- Web auth: tokens live in httpOnly cookies set by server actions (`src/actions/auth.ts`);
  page code never sees them. Server components call the API through `serverApi()` (anonymous)
  or `authedApi()` (signed in).
- Buyer-facing responses come from `ListingDetail`; the seller's own view is a separate
  endpoint (`/listings/{id}/manage`) returning `SellerListingDetail`, so private fields
  cannot leak through a shared response model.
- All API calls go through `@thiqa/api-client` — never hand-write fetch URLs or response types.
- Design values come from `@thiqa/ui` tokens (Tailwind classes like `bg-brand-700`,
  `text-neutral-700`; RN via `src/theme.ts`). No ad-hoc hex colors.
- Prettier: single quotes, trailing commas, width 100.

## i18n / RTL (non-negotiable)

- Arabic is the default locale; English secondary. Messages live in
  `packages/i18n/messages/{ar,en}.json` (ICU format) and are shared by web and mobile.
  A test fails if the key sets differ.
- Every user-facing string goes through `t()`. Never concatenate translated strings —
  use ICU placeholders (`"الإصدار {version}"`).
- Web: Arabic at `/`, English at `/en`; `<html lang dir>` set per locale; browser language
  is ignored (Arabic-first), the switcher sets a cookie.
- Mobile: native layout forced RTL; the root view sets `direction` per locale.
- Use logical layout only: Tailwind `ms-/me-/ps-/pe-/start-/end-`, `text-start`; in RN use
  `start/end`, `marginStart/End`. Never `left/right`, `ml-/mr-`, `text-left`.
- Numeric inputs (price, mileage, year, phone) go through `parseIntInput` / `parse_int`
  (Arabic-Indic digits). Search text through `normalizeArabic` / `normalize_arabic`.
  TS and Python implementations share `packages/i18n/test-cases/normalize.json`.
- Font: IBM Plex Sans Arabic. Tap targets ≥ 44px. Screen-reader labels in both languages.

## Git

- Small, focused commits with clear messages. Update `PROGRESS.md` at the end of each phase.
- Generated files (`packages/api-client/openapi.json`, `src/schema.d.ts`, `packages/ui/theme.css`)
  are committed; CI fails if they are stale.
