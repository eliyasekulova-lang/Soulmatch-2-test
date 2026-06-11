# Phase 0 Foundation Reset

Last updated: 2026-02-13

## 1. Clean environment / remove dev shortcuts

- `APP_ENV` is now explicit (`development`, `staging`, `production`, `test`).
- Production/staging boot now fails fast if:
  - `JWT_SECRET` is missing/default.
  - `DATABASE_URL` is missing.
  - `CORS_ALLOW_ORIGINS` is missing.
- CORS is strict allowlist only (no wildcard behavior).

## 2. Reproducible dependency workflow

- Python dependencies are pinned in `services/api/requirements.txt`.
- Node dependencies are locked via `apps/mobile/package-lock.json`.
- Install commands:
  - API: `pip install -r requirements.txt`
  - Mobile: `npm ci`

## 3. Environment split

- API templates:
  - `services/api/.env.development.example`
  - `services/api/.env.staging.example`
  - `services/api/.env.production.example`
- Mobile runtime environment via:
  - `EXPO_PUBLIC_ENV`
  - `EXPO_PUBLIC_API_BASE_URL`

## 4. Structured logging and error tracking

- JSON request logging is enabled in API middleware.
- Correlation header `x-request-id` is emitted for each response.
- Optional Sentry integration:
  - Set `SENTRY_DSN` and `SENTRY_ENVIRONMENT`.
  - If unset, API runs without external error reporting.
