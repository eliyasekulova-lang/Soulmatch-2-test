# SoulMatch

Mobile-first matchmaking and social discovery app using astrology + psychology + ML-inspired vectors.

This repo contains an MVP scaffold:
- `apps/mobile`: React Native (Expo) client
- `services/api`: FastAPI backend
- `docs/`: Product, UX, data, and architecture specs

## Quick start (dev)

### API
```
cd services/api
python3 -m venv ~/.venvs/soulmatch-api
source ~/.venvs/soulmatch-api/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.development.example .env
set -a && source .env && set +a
alembic upgrade head
uvicorn app.main:app --reload
```

For highest-accuracy Swiss Ephemeris results, download ephemeris files and set `EPHE_PATH` to the directory.
If files are missing in local dev, API falls back to Moshier so onboarding still works.
To seed demo candidates from backend (instead of mobile), run:
```
cd services/api
python scripts/seed_candidates.py
```
Or call `POST /admin/seed-candidates` as an authenticated admin user (`role=admin`).
Run API integration tests:
```
cd services/api
pytest -q
```

### Mobile
```
cd apps/mobile
npm ci
npm run start:dev
```
Env-based API config is in `apps/mobile/src/config.js`.
Override with:
- `EXPO_PUBLIC_ENV=development|staging|production`
- `EXPO_PUBLIC_API_BASE_URL=https://your-api`

## What is included
- AstroVector schema (v0) and similarity-based matching
- Full onboarding flow in mobile app (identity, birth data, place picker, goals, consent)
- Client-side place picker with latitude/longitude/timezone capture
- Match flow with romance/friendship mode toggle and API-ranked match cards
- API endpoints for user creation, vector generation, and matching
- PostgreSQL persistence for users, vectors, and match results
- Backend-side candidate seeding script and admin endpoint
- JWT auth endpoints (`/auth/signup`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`)
- Consent logging and analytics event ingestion (`/events`)
- Alembic migrations and GitHub Actions CI/CD workflows
- Swiss Ephemeris powered chart computation (via `pyswisseph`)

## Notes
This is a functional MVP scaffold intended for rapid iteration. Production concerns like auth, payments, and compliance are outlined in `docs/`.
Birthplace geocoding uses OpenStreetMap Nominatim; for scale, pass latitude/longitude/timezone directly or use a paid geocoder.
CI/CD and secret requirements are documented in `docs/DEPLOYMENT.md`.

## Environment config split
- API:
  - `services/api/.env.development.example`
  - `services/api/.env.staging.example`
  - `services/api/.env.production.example`
- Mobile:
  - `EXPO_PUBLIC_ENV=development|staging|production`
  - `EXPO_PUBLIC_API_BASE_URL=<api-base-url>`
