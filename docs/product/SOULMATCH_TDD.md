# SoulMatch Technical Design Document (TDD)
Version: v1.0
Date: 2026-02-14

## 1. Scope
This design implements the PRD for an astrology + psychology + behavior compatibility platform with strong Trust & Safety. The backend is TypeScript + Postgres + Redis/BullMQ.

## 2. Architecture
- API: Fastify (REST + OpenAPI)
- DB: PostgreSQL (SQL migrations)
- Queue/Jobs: Redis + BullMQ
- Cache: Redis
- Auth: JWT access/refresh tokens
- Observability: structured logs + request IDs + audit events

## 3. Core Services
- `auth`: signup/login/token lifecycle
- `profile`: user profile, birth data, preferences
- `astrology`: natal + synastry calculations API boundary
- `onboarding`: psych/intent/lifestyle answers
- `behavior`: event ingest + profile aggregation
- `matches`: scoring + feeds + explanations + prediction
- `messaging`: conversations/messages + idempotency
- `media`: presign/attach/get flow (storage abstraction)
- `openers`: opening message suggestions
- `advisor`: forward-only advisor policy
- `safety`: reports/blocks/tips + risk pipeline integration
- `admin`: safety audit and weight management (RBAC)

## 4. Data Model (Phase-1 baseline)
Key entities:
- users, birth_data, psych_profiles, behavior_signal_events, behavior_profiles
- natal_charts, match_scores, conversations, messages
- reports, blocks, trust_safety_risks, safety_action_logs
- policy_documents, policy_versions, consent_events
- user_rights_requests, deletion_jobs, audit_events, media_objects

Non-negotiable policy:
- `trust_safety_risks` is internal-only.
- No public DTO includes riskScore/riskBand/reasonCodes.

## 5. Matching Engine
- Layer scores normalized [0..1]
- Attraction formula:
  - `A = wA*astrologyChem + wP*psychChem + wB*behaviorChem + wI*intent + wL*alignment`
- Destiny formula:
  - `D = wA2*astrologyStab + wP2*psychStab + wB2*behaviorStab + wI2*intent + wL2*alignment`
- Weights stored in DB and adjustable via admin endpoints.

## 6. Trust & Safety Engine
- Triggered on message/report and nightly batch
- Risk bands:
  - low 0-24, medium 25-49, high 50-74, critical 75-100
- Policy actions:
  - medium: mild throttles + contextual safety tips
  - high: stronger throttles + visibility reduction + coercion auto-hide
  - critical: severe throttles + forced verification + shadow limitation + admin review
- Server-only risk persistence in `trust_safety_risks`.

## 7. Advisor Policy Guardrails
- Allowed: forward-looking coaching prompts
- Blocked: backward-looking failure analysis requests
- On blocked intent: return safe alternative guidance prompt.

## 8. Jobs
- `behavior-aggregation`: nightly rolling behavior profile updates
- `safety-scoring`: key event + nightly risk recomputation
- `deletion-jobs`: scrub user data + media deletion + backup eventual deletion metadata
- `export-jobs`: generate JSON bundle + ZIP + expiring link metadata

## 9. Security
- JWT auth, RBAC for admin routes
- Rate limits for auth/rights/safety endpoints
- Input validation on all public APIs
- Secrets from environment only
- TLS assumed at edge
- Append-only audit event logs

## 10. Milestone Acceptance Gates
- M1..M6 map directly to PRD acceptance criteria and are tracked in implementation task list.

## 11. Known Phase-1 Constraints
- Astrology internals may call external compute service boundary first.
- Message text storage can be reduced later via content-ref architecture.
- Composite chart and advanced timing intelligence are staged for later milestone.
