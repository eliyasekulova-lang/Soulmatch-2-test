# Architecture (MVP)

## Stack
- Mobile: React Native (Expo)
- API: FastAPI (Python)
- DB: PostgreSQL
- Cache/Queue: Redis
- Vector search: FAISS (later)
- Astro engine: Swiss Ephemeris (pyswisseph)

## Services
- API service handles onboarding, vector generation, matching, and chat
- ML jobs (later) handle learned features and re-ranking
- Data persistence uses SQLAlchemy models on PostgreSQL (`users`, `astro_vectors`, `match_results`)
- Demo candidate seeding is handled server-side via `scripts/seed_candidates.py` or `/admin/seed-candidates`

## Security
- JWT auth for mobile/API sessions
- Encrypt birth data at rest
- TLS in transit
- Data deletion on request
- Consent records stored with policy version and timestamp

## Global Use
- Birthplace geocoding via OpenStreetMap (Nominatim)
- Timezone resolution via TimezoneFinder
- Accept direct lat/lon/timezone to avoid API dependency

## Scaling Path
- Add vector index (FAISS/Annoy)
- Split chat into separate service
- Add background jobs for analytics
- Add managed metrics backend for analytics events (`analytics_events`)
