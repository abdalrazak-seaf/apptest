import { defineConfig, devices } from '@playwright/test';

const API_PORT = Number(process.env.E2E_API_PORT ?? 8100);
const WEB_PORT = Number(process.env.E2E_WEB_PORT ?? 3100);
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined;

// A database of its own, so end-to-end rows never mix with the unit tests' data.
const DATABASE_URL =
  process.env.E2E_DATABASE_URL ?? 'postgresql+asyncpg://thiqa:thiqa@localhost:5432/thiqa_e2e';
// Known admin, created at start-up, used to approve listings during the tests.
export const ADMIN_PHONE = '0500000009';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: 'retain-on-failure',
    launchOptions: { executablePath },
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: [
    {
      // Migrate, seed the reference data and create the admin, then serve.
      command: [
        'uv run alembic upgrade head',
        'uv run python -m api.scripts.seed',
        `uv run python -m api.scripts.promote_admin ${ADMIN_PHONE}`,
        `uv run uvicorn api.main:app --port ${API_PORT}`,
      ].join(' && '),
      cwd: '../api',
      // Readiness, not liveness: if Postgres or Redis is missing the run fails here with a
      // clear timeout, instead of every login-dependent test failing for an unclear reason.
      url: `http://localhost:${API_PORT}/health/ready`,
      env: {
        APP_ENV: 'test',
        // Photos live in memory, so end-to-end runs need no object storage.
        STORAGE_PROVIDER: 'memory',
        DATABASE_URL,
        JWT_SECRET: 'end-to-end-secret-that-is-long-enough-32',
        // Lets the tests read the login code from the page instead of the logs.
        OTP_EXPOSE_CODE: 'true',
        OTP_REQUESTS_PER_WINDOW: '100',
      },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `pnpm exec next start --port ${WEB_PORT}`,
      url: `http://localhost:${WEB_PORT}`,
      env: { API_INTERNAL_URL: `http://localhost:${API_PORT}` },
      reuseExistingServer: !process.env.CI,
    },
  ],
});
