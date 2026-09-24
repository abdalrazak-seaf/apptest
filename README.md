# [APP_NAME] — codename Thiqa (ثقة)

AI-first used-car marketplace for Saudi Arabia. Product spec: [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md) ·
status: [`PROGRESS.md`](PROGRESS.md) · conventions: [`CLAUDE.md`](CLAUDE.md).

## Quick start

Requirements: Docker, Node 22 + pnpm 10 (`corepack enable`), [uv](https://docs.astral.sh/uv/).

```bash
make setup     # dependencies, git hooks, .env
make dev       # Postgres/Redis/MinIO/Mailpit + API + worker + web
```

- Web: http://localhost:3000 (Arabic, RTL) · English: http://localhost:3000/en
- API: http://localhost:8000/health · docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001 (minioadmin/minioadmin) · Mailpit: http://localhost:8025

Mobile: `make dev-mobile`, then open in Expo Go (set `EXPO_PUBLIC_API_URL` in `apps/mobile/.env`
to your computer's LAN IP when using a physical phone).

`make help` lists every command.
