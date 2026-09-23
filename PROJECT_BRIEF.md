# PROJECT BRIEF — [APP_NAME] (codename: Thiqa / ثقة)
### AI-first used-car marketplace for Saudi Arabia — build instructions for Claude Code

> **How to use this file:** Put it in the root of an empty git repository, open Claude Code in that folder, and say:
> *"Read PROJECT_BRIEF.md fully, then start Phase 0. Stop at the end of each phase for my review."*

---

## 0. Your role and working rules (read first)

You are the lead engineer building a production-quality MVP. Follow these rules for the entire project:

1. **Work phase by phase** (Section 9). Do not start a phase until I approve the previous one. At the end of each phase: run all tests, run lint and type checks, update `PROGRESS.md`, and give me a short summary with what to test manually.
2. **Create `CLAUDE.md` in Phase 0** with the conventions from this brief (stack, commands, folder layout, coding standards) so future sessions stay consistent. Keep it updated.
3. **Ask before** adding a new paid third-party service, changing the stack, or making a decision this brief marks as "open".
4. **Never hardcode secrets.** Everything goes through environment variables with a documented `.env.example`.
5. **Every external integration sits behind an interface** with a working mock/sandbox implementation, so the app runs fully offline in local development (SMS, payments, vehicle history, inspection partners, LLM).
6. **Tests are part of "done".** Unit tests for business logic, API tests for every endpoint, and at least one end-to-end happy path per phase.
7. **Arabic-first.** Every user-facing string goes through i18n (Arabic default, English secondary). All layouts must work in RTL. Never concatenate translated strings.
8. **Do not scrape Haraj or any other platform.** Seed data comes only from the import tools in Phase 3 using data I supply.
9. Prefer boring, well-documented technology. Small, readable modules over clever abstractions.

---

## 1. Product summary

**Positioning:** Haraj helps you find a buyer. We help you close the deal — safely and at the right price.

**Ideal customer (ICP):** Private used-car sellers and small independent showrooms (معارض) in Saudi Arabia selling cars in roughly the SAR 30K–200K range. Buyers are the other side of the marketplace.

**Core pain point we solve:** Used-car deals are slow and low-trust because nothing can be verified — the car's real condition, the fair price, or the credibility of the other party. Sellers waste time on unserious buyers and lowballers; buyers waste time on cars that don't match their listings and fear fraud.

**MVP scope:** Cars only. Launch city: Riyadh (but the data model supports all Saudi cities from day one).

**The four AI pillars (the product's differentiation):**
1. **AI Listing Builder** — photos → structured, complete listing in ~2 minutes.
2. **Fair-Price Engine** — price band and "fair / high / great deal" badge with confidence.
3. **AI Deal Agent** — Saudi-dialect assistant that answers buyer questions, screens lowballers, and books viewings on the seller's behalf.
4. **Trust & Fraud Layer** — duplicate-photo detection, price anomaly detection, scam-message detection, and a transparent trust score.

**Plus:** conversational search in Saudi Arabic, transparent moderation (every rejected or hidden listing shows a reason), and transparent flat-fee monetization instead of an honor-based commission.

**North-star metrics (instrument from day one):** days-to-sale, final sale price vs. asking price, time to first *qualified* inquiry, share of buyer messages handled by the Deal Agent, fraud flags per 1,000 listings.

---

## 2. Explicit non-goals for the MVP

- No categories other than cars (no real estate, electronics, livestock, etc.).
- No escrow or holding of buyer funds (this requires a licensed payment partner — design an interface only, see Phase 6).
- No direct financing integration (referral links only).
- No direct government system integrations (Absher/Tamm ownership transfer is a link-out with instructions; Nafath identity verification and vehicle-history providers are interfaces with mocks).
- No custom-trained computer-vision models yet. Use a multimodal LLM for vision in the MVP; keep the interface ready for replacement.

---

## 3. Tech stack (decided)

| Layer | Choice |
|---|---|
| Repo | Monorepo (pnpm workspaces + Turborepo for JS; `uv` for Python) |
| Backend API | Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2 |
| Background jobs | ARQ (Redis-based) workers |
| Database | PostgreSQL 16 with PostGIS and pgvector extensions |
| Cache / pubsub | Redis |
| Object storage | S3-compatible API (MinIO locally) |
| Realtime chat | WebSockets in FastAPI + Redis pub/sub |
| Web app | Next.js (App Router), TypeScript, Tailwind CSS, next-intl, RTL-first |
| Mobile app | Expo (React Native), TypeScript, Expo Router, i18n with RTL |
| API client | TypeScript client generated from FastAPI's OpenAPI spec, shared by web and mobile |
| ML | scikit-learn + LightGBM, pandas, imagehash (perceptual hashing) |
| LLM | Anthropic Claude API behind an `LLMProvider` interface. Model names come from env vars: `LLM_MODEL_SMART` (e.g. `claude-sonnet-5`) for the Deal Agent and listing writing, `LLM_MODEL_FAST` (e.g. `claude-haiku-4-5-20251001`) for classification and search parsing |
| Local dev | Docker Compose (Postgres, Redis, MinIO, Mailpit) + `make` targets |
| Testing | pytest, httpx; Vitest + Playwright (web); Jest (mobile logic) |
| Quality | ruff + mypy (Python); ESLint + Prettier + tsc (TS); pre-commit hooks |
| CI | GitHub Actions: lint, type check, tests, build |

**Hosting note (open decision — ask me before Phase 7):** Personal data must comply with Saudi PDPL, so production should run in a cloud region located in Saudi Arabia. Keep all infra config region-agnostic until I decide the provider.

---

## 4. Repository layout

```
/apps
  /api          FastAPI app (routers, services, models, schemas)
  /worker       ARQ background jobs (AI pipelines, pricing, fraud scans)
  /web          Next.js buyer/seller web app + showroom dashboard + admin
  /mobile       Expo app (buyer + seller)
/packages
  /api-client   Generated TypeScript client
  /ui           Shared design tokens (colors, spacing, typography)
  /i18n         Shared translation files (ar, en)
/ml
  /pricing      Training, evaluation, and model registry for the Fair-Price Engine
  /fraud        Rules and scoring for the Trust & Fraud Layer
/infra          docker-compose, Dockerfiles, CI workflows
/docs           Architecture notes, ADRs, API docs
CLAUDE.md  PROGRESS.md  PROJECT_BRIEF.md  .env.example  Makefile
```

---

## 5. Domain model (initial — refine as needed, document changes in an ADR)

- **User** — id, phone (unique, E.164), name, preferred_language, role (`buyer`, `seller`, `showroom_staff`, `admin`), city, identity_verified (bool), identity_provider, created_at.
- **Showroom** — id, name_ar, name_en, commercial_registration_number, city, location (PostGIS point), logo, verified (bool), subscription_tier, staff (many users).
- **Vehicle taxonomy** — `Make`, `Model`, `Trim` (with Arabic + English names and aliases, e.g. "جمس" → GMC, "لاندكروزر" → Land Cruiser). Seed with the top makes/models in the Saudi market.
- **Listing** — id, seller (user or showroom), make, model, trim, year, mileage_km, body_type, transmission, fuel_type, engine, color, regional_spec (Saudi/GCC/American/other), accident_history_declared, service_history_declared, asking_price_sar, floor_price_sar (private, never exposed to buyers), city, location, description_ar, description_en, status, status_reason_code, created_at, sold_at, final_price_sar.
- **ListingStatus** — `draft`, `pending_review`, `active`, `hidden`, `rejected`, `sold`, `expired`. Every non-active status **must** carry a `status_reason_code` and a human-readable reason shown to the seller (fixes the "my post was not published and nobody told me why" problem).
- **ListingPhoto** — id, listing, storage_key, order, perceptual_hash, ai_tags (JSON), damage_flags (JSON).
- **ConditionReport** — id, listing, source (`ai_photo`, `physical_inspection`), summary, findings (JSON list with severity), odometer_reading_from_photo, confidence, created_at.
- **PriceEstimate** — id, listing, model_version, p10, p50, p90, badge (`great_deal`, `fair`, `high`, `insufficient_data`), confidence, comparables (JSON list of listing ids), created_at.
- **Conversation / Message** — buyer, listing, messages with sender type (`buyer`, `seller`, `agent`, `system`), content, language, fraud_score, created_at.
- **AgentSettings** (per listing) — mode (`off`, `draft_for_approval`, `auto_reply`), floor_price_sar, negotiable (bool), availability windows for viewings, facts the seller has confirmed (JSON), handoff rules.
- **BuyerQualification** — conversation, score (0–100), signals (JSON: budget stated, offer vs. asking, responsiveness, identity verified, location), label (`qualified`, `unclear`, `lowball`, `suspicious`).
- **Viewing** — listing, buyer, seller, scheduled_at, location, status.
- **Review** — reviewer, reviewee, listing, rating (1–5), comment, verified_deal (bool — only allowed after a completed viewing or marked sale).
- **TrustScore** — user, score (0–100), components (JSON), computed_at. Components must be explainable to the user.
- **FraudFlag** — entity type/id, flag_type, severity, evidence (JSON), status (`open`, `dismissed`, `actioned`), reviewed_by.
- **Payment / Subscription / InspectionBooking** — see Phase 6.
- **Event** — analytics events (listing_viewed, contact_started, qualified_inquiry, viewing_booked, marked_sold, etc.) for north-star metrics.

---

## 6. Cross-cutting requirements

**Localization**
- Arabic is the default locale; full RTL on web and mobile.
- Normalize Arabic-Indic digits (٠١٢٣) and Western digits in all numeric inputs (price, mileage, year, phone).
- Normalize common Arabic spelling variants in search (أ/إ/آ → ا, ة/ه, ى/ي, removal of tatweel and diacritics).
- Currency SAR, distances in km, Saudi city list seeded (Riyadh, Jeddah, Makkah, Madinah, Dammam, Khobar, Dhahran, Qassim/Buraidah, Abha, Tabuk, Hail, Jazan, Najran, Taif, Al-Ahsa, etc.).

**Security and privacy**
- Phone OTP authentication (SMS provider behind an interface; mock prints OTP to logs in dev). Rate-limit OTP requests.
- JWT access + refresh tokens; refresh token rotation.
- Role-based access control on every endpoint; tests for authorization failures.
- Phone numbers are never shown publicly; contact happens through in-app chat (with optional reveal the seller controls).
- `floor_price_sar` is never returned by any buyer-facing endpoint — write a test that proves it.
- PII minimization, audit log for admin actions, data export and account deletion endpoints (PDPL readiness).
- Input validation on every endpoint; file upload type/size validation; signed URLs for media.

**AI safety and cost controls**
- All LLM calls go through `LLMProvider` with: timeouts, retries, per-user rate limits, token usage logging, and a monthly cost counter visible in admin.
- All LLM outputs that feed the database are validated against Pydantic schemas; on invalid output, retry once, then fall back gracefully.
- Store prompts as versioned templates in code (`/apps/api/prompts/`), not inline strings.
- A mock LLM provider returns deterministic fixtures so tests never hit the real API.

**Observability**
- Structured JSON logs, request ids, basic metrics endpoint, error tracking hook (provider TBD).

---

## 7. The four AI pillars — detailed specs

### 7.1 AI Listing Builder
**Flow:** Seller uploads 4–20 photos (optionally a short walkaround video — MVP extracts ~8 frames) → worker job runs → seller gets a pre-filled listing form to review and edit → publish.

**Pipeline:**
1. Validate and store photos; compute perceptual hashes (feeds fraud checks).
2. Vision LLM call per photo batch returning strict JSON: `{make, model, year_range, body_type, color, angle, visible_damage[] (type, location, severity), odometer_reading (if dashboard visible), confidence}`.
3. Map make/model text to taxonomy ids using aliases + fuzzy matching; if confidence is low, leave the field empty for the seller rather than guessing.
4. Generate `description_ar` (natural Saudi-friendly Arabic, factual, no exaggeration, no invented claims) and `description_en`, using only confirmed fields.
5. Produce an `ai_photo` ConditionReport with findings and an explicit disclaimer that it is an automated visual check, not a physical inspection.
6. Suggest missing photo angles ("add a photo of the dashboard with the engine on").

**Rules:** The seller must confirm every AI-filled field before publishing. The UI clearly marks AI-suggested values. Never fabricate accident or service history.

**Acceptance:** A seller can go from photos to published listing in under 3 minutes in the happy path; mapping accuracy tests run on a fixtures set of labeled images I will provide (create the test harness and a small placeholder set).

### 7.2 Fair-Price Engine
**Goal:** Output a price band (p10/p50/p90), a badge, and a confidence level for every active listing.

**Approach:**
- **Data:** Build an import tool (`make import-price-data FILE=...`) that loads CSV data I supply (columns documented in `/ml/pricing/README.md`), plus our own listings and `final_price_sar` of sold listings (weighted higher than asking prices).
- **Model:** LightGBM quantile regression (three models: 0.1, 0.5, 0.9) on features: make, model, trim, year/age, mileage, city, regional_spec, body_type, transmission, fuel_type, condition findings severity, accident_history_declared, seller type (private/showroom), listing month.
- **Cold start / low data:** If a segment has too few comparables, fall back to a k-nearest-comparables estimate; if still insufficient, return `insufficient_data` and **show no badge**. Never show a confident badge on thin data.
- **Badge logic:** `great_deal` if asking < p25-equivalent threshold, `fair` inside the band, `high` above p90 — thresholds configurable.
- **Explainability:** Return the top 3–5 comparable listings and the main factors ("mileage below average for this year").
- **Seller-side:** On listing creation, show "likely to sell within X days at this price" as a *later* enhancement — for now show the band and a suggestion.
- **MLOps-lite:** Versioned model artifacts in `/ml/pricing/models/`, an evaluation script reporting MAE and interval coverage by segment, and a nightly retrain job (disabled by default).

**Acceptance:** Evaluation report generated on the seed data; API returns estimates in < 300 ms from cache; badge is suppressed when confidence is low (tested).

### 7.3 AI Deal Agent
**Goal:** Save sellers time by handling repetitive buyer messages and screening buyers, while staying honest and under seller control.

**Modes (per listing, seller-controlled):**
- `off` — no agent.
- `draft_for_approval` (default) — agent drafts replies; seller approves/edits with one tap.
- `auto_reply` — agent replies directly within its rules.

**Capabilities:**
- Answer factual questions using **only** listing data, the condition report, and facts the seller has confirmed in AgentSettings. If it doesn't know, it says so and escalates to the seller.
- Handle availability and "last price?" questions. May negotiate within the seller's settings: never agree below `floor_price_sar`, never reveal the floor, never make commitments beyond price and viewing time.
- Qualify buyers: compute BuyerQualification from signals; label lowball offers politely; surface qualified buyers first in the seller's inbox.
- Book viewings inside the seller's availability windows; create a Viewing record and notify both parties.
- Respond in the buyer's language/dialect (Saudi Arabic or English).

**Guardrails (must be enforced in code, not only in the prompt):**
- The agent is always disclosed to the buyer (e.g. label "مساعد البائع الذكي" on its messages).
- Post-generation validator checks: no price below floor, no floor disclosure, no claims absent from the allowed facts, no external payment links, no requests for deposits. Violating drafts are blocked and escalated.
- Immediate handoff to the seller on: complaints, legal questions, requests to pay outside the platform, suspicious messages, or any repeated confusion.
- Full audit trail of agent messages visible to the seller.

**Acceptance:** A scripted evaluation set of at least 40 buyer conversations (Arabic and English, including lowballers and scam attempts) with automated checks for every guardrail — create the harness and initial cases.

### 7.4 Trust & Fraud Layer
**Signals:**
- **Duplicate/stolen photos:** perceptual-hash matching across listings (different sellers, same photos → flag).
- **Price anomaly:** asking price far below the Fair-Price p10 for its segment (classic scam bait) → flag for review.
- **Message risk:** rules + fast-LLM classifier for scam patterns (off-platform payment requests, deposit before viewing, urgency pressure, suspicious links, "I'm abroad, shipping the car" stories). Show buyers an in-chat safety warning when triggered.
- **Account signals:** new account + many listings, many near-identical listings, rapid edits to price/photos.

**Trust Score (0–100), explainable, shown on profiles:** identity verified, showroom verified, completed deals, verified-deal reviews average, response rate/time, account age, and open fraud flags (negative). The profile shows *why* ("verified identity ✓, 12 completed deals, replies within 1 hour").

**Seller ratings:** Restore and improve seller ratings — buyers can sort and filter by trust score and rating (directly requested by users in Haraj reviews). Reviews only allowed after a completed viewing or marked sale.

**Moderation console (admin web):** queue of FraudFlags and pending listings, evidence view, actions (dismiss, hide listing with reason code, suspend account), audit log.

**Acceptance:** Seeded scenarios (duplicate photos, below-market bait listing, scam message) each produce the correct flag and user-facing effect, covered by tests.

### 7.5 Conversational search
- Search box accepts free text in Saudi Arabic or English, e.g. "أبي جمس ٢٠١٩ نظيف تحت ٩٠ ألف في الرياض".
- Fast LLM converts the query into a validated filter JSON (make, model, year range, max price, city, max mileage, condition preferences, sort). Show the parsed filters as editable chips so the user sees and corrects the interpretation.
- Fallback: normalized Arabic full-text search in PostgreSQL if parsing fails.
- Cache parsed queries; standard structured filters and sorting (price, year, mileage, newest, trust score) always available without AI.

---

## 8. Core marketplace features (non-AI, required)

- Browse and search without signing up (matches Haraj's low-friction strength); sign-up required to post or chat.
- Listing detail page: photos gallery, specs, AI condition report, price badge, seller trust panel, map (approximate location only), "similar cars".
- In-app chat with read receipts, image sharing, safety tips, block/report.
- Favorites and saved searches with push/email notifications for new matches.
- Seller dashboard: my listings with status and reason codes, views, inquiries (sorted by qualification), viewings calendar, mark as sold (captures final price — feeds the pricing engine).
- Showroom dashboard (web): multi-user staff, bulk listing import via CSV, inventory view, performance metrics (days-to-sale, inquiries per listing).
- SEO-friendly public listing pages on web (server-rendered, structured data for vehicles).
- Ownership-transfer guide page (link-out and step-by-step instructions; no integration).

---

## 9. Build phases and acceptance criteria

**Phase 0 — Foundation**
Monorepo scaffold, Docker Compose, Makefile (`make dev`, `make test`, `make lint`, `make migrate`, `make seed`), CI pipeline, `CLAUDE.md`, `PROGRESS.md`, `.env.example`, i18n and RTL setup on web and mobile, design tokens, health checks, OpenAPI → TS client generation.
*Done when:* `make dev` brings up everything locally; web and mobile show an Arabic RTL placeholder screen calling the API health endpoint; CI is green.

**Phase 1 — Core marketplace**
Auth (phone OTP, mock SMS), users, showrooms, vehicle taxonomy seed, listings CRUD with manual form, photo upload, statuses with reason codes, search with structured filters, listing pages, chat (WebSockets), favorites, saved searches, seller dashboard basics, admin basics. Analytics events.
*Done when:* a seller can post a car manually, a buyer can find it, chat, and the seller can mark it sold with a final price — end-to-end test passes on web; mobile covers browse, listing detail, chat, and posting.

**Phase 2 — AI Listing Builder** (Section 7.1).

**Phase 3 — Fair-Price Engine** (Section 7.2), including the CSV import tool and evaluation report.

**Phase 4 — AI Deal Agent** (Section 7.3), including the conversation evaluation harness.

**Phase 5 — Trust & Fraud Layer + conversational search** (Sections 7.4 and 7.5), including ratings, trust score, and the moderation console.

**Phase 6 — Monetization and partners**
- `PaymentProvider` interface with a mock implementation and one sandbox adapter for a Saudi payment gateway (ask me which provider before implementing; support mada, Apple Pay, and cards via the provider).
- Products: **Verified Listing** (flat fee: AI report + badge + priority placement), **Showroom subscription** tiers (listing limits, dashboard analytics, Deal Agent auto-reply mode), **Physical inspection booking** via an `InspectionPartner` interface (mock partner in dev), **Financing referral** links with tracking.
- Invoices/receipts in Arabic and English, VAT-ready fields (15% VAT configurable).
- Escrow: design document only (`/docs/escrow.md`) describing how it would work with a licensed partner — no implementation.

**Phase 7 — Hardening and launch readiness**
Security review checklist (OWASP top 10) with fixes, load test on search and listing pages, image optimization/CDN config, backup/restore docs, admin analytics dashboard for north-star metrics, production deployment config for the cloud provider I choose (ask me), app store build configuration for the Expo app.

---

## 10. UX and design direction

- Clean, modern, trustworthy — deliberately more polished than classic classifieds apps. Generous whitespace, large photos, clear hierarchy.
- Trust signals are first-class UI elements: price badge, condition report summary, and seller trust panel appear above the fold on listing pages.
- Every AI output is labeled as AI and editable or dismissible.
- Arabic typography: use a high-quality Arabic font with good numerals (e.g. IBM Plex Sans Arabic or Tajawal), with a Latin companion.
- Mobile-first; the seller posting flow must be one-handed and completable in under 3 minutes.
- Accessibility: sufficient contrast, screen-reader labels in both languages, tap targets ≥ 44px.

---

## 11. Open decisions (ask me when you reach them)

1. Final app name and brand colors (use `[APP_NAME]` and neutral tokens until then).
2. Cloud provider and Saudi region for production (Phase 7).
3. Payment gateway provider (Phase 6).
4. SMS/OTP provider (mock until then).
5. Identity verification provider for Nafath-based verification (interface + mock until then).
6. Vehicle-history data provider (interface + mock until then).
7. Inspection partner(s) (mock until then).
8. Pricing badge thresholds and Verified Listing / subscription prices.

---

## 12. Definition of done (every phase)

- All acceptance criteria for the phase met.
- Tests, lint, and type checks pass locally and in CI.
- Migrations are reversible.
- New env vars documented in `.env.example`.
- Arabic and English strings complete; RTL checked on web and mobile.
- `PROGRESS.md` updated: what was built, how to test it manually, known issues, next steps.
- Short summary sent to me, then **stop and wait for approval**.
