# SoulMatch API TS — Milestone 1 Only

This service intentionally implements **Milestone 1 only**:
- Auth (`/auth/signup`, `/auth/login`)
- Profile (`GET/PUT /profile`, `POST /profile/birthdata`)
- Onboarding skeleton (`GET /onboarding/questions`, `POST /onboarding/answers`)
- Event pipeline scaffold (`POST /events`)

No M2+ features are implemented in this folder.

## Local dev
1. `cp .env.example .env`
2. Set `DATABASE_URL` to your local Postgres
3. `npm install`
4. `npm run migrate`
5. `npm run dev`
