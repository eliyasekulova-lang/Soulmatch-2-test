# SoulMatch API (TypeScript)

Compliance-first backend scaffold based on the PRD.

## Stack
- Fastify + TypeScript
- Postgres
- Redis + BullMQ

## Run Local
1. `cp .env.example .env`
2. `docker compose up -d`
3. Set `DATABASE_URL=postgres://postgres:postgres@localhost:5434/soulmatch_ts`
4. Set `REDIS_URL=redis://localhost:6380`
5. `npm install`
6. `npm run migrate`
7. `npm run dev`

## OpenAPI
- Interactive docs: `/docs`
- Export JSON: `npm run openapi`

## Safety Constraint
`trust_safety_risks` is server-internal only and is not returned in public DTOs.

## Implemented Endpoint Surface
- Auth: `POST /v1/auth/signup`, `POST /v1/auth/login`
- Profile: `GET/PUT /v1/profile`, `POST /v1/profile/birthdata`, `GET /v1/me`, `PATCH /v1/me`
- Astrology: `POST /v1/astrology/natal`, `POST /v1/astrology/synastry`
- Onboarding: `GET /v1/onboarding/questions`, `POST /v1/onboarding/answers`
- Behavior: `POST /v1/events`, `GET /v1/profile/behavior`
- Matches: `GET /v1/matches`, `GET /v1/matches/:id/explain`, `GET /v1/matches/:id/prediction`
- Messaging: `POST /v1/conversations`, `GET /v1/conversations`, `POST /v1/messages`, `GET /v1/messages`
- Media: `POST /v1/media/presign`, `POST /v1/media/:id/attach`, `GET /v1/media/:id`
- Openers: `GET /v1/matches/:id/openers`
- Advisor: `POST /v1/advisor` (forward-only guard)
- Safety: `POST /v1/reports`, `POST /v1/block`, `POST/DELETE /v1/blocks`, `GET /v1/safety/tips`
- Rights: `POST /v1/rights/export`, `POST /v1/rights/delete`, `GET /v1/rights/requests`
- Admin: `GET /v1/admin/safety/audit`, `GET/PUT /v1/admin/weights`, `GET /v1/admin/reports`, `POST /v1/admin/reports/:id/actions`, `POST /v1/admin/users/:id/suspend`, `POST /v1/admin/users/:id/ban`, `GET /v1/admin/audit`

## Jobs
- behavior aggregation queue
- safety scoring queue
- deletion jobs queue
- export jobs queue

## Notes
This is production-oriented scaffolding with core formulas, detectors, and policy engine primitives. Wire real persistence/services next in each module implementation.
