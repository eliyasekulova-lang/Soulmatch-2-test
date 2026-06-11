# Soulmatch Production Execution Plan

Status: Active  
Last updated: 2026-02-13

## Current Execution Status (2026-02-18)

- Phase 0: Complete
- Phase 1: Complete
- Phase 2: Complete (baseline legal/compliance + consent/rights + audit)
- Phase 3: In progress (astrology quality hardening remaining)
- Phase 4: Complete (psych onboarding + profile integration)
- Phase 5: Complete (hybrid match/explain/prediction baseline)
- Phase 6: In progress (UI/brand polish and production UX pass pending)
- Phase 7.1-7.6 hardening: Complete
  - 7.1 config/secret guards
  - 7.2 security controls
  - 7.3 health + telemetry
  - 7.4 startup/lifespan modernization
  - 7.5 release gate + CI enforcement
  - 7.6 deployment/rollback runbook and post-deploy verifier

## Product Standard

1. No temporary hacks in production paths.
2. Security/privacy/compliance by design.
3. Deterministic matching pipeline + explainability.
4. Measurable quality gates before launch.

---

## Phase 0: Foundation Reset (Now, 2-4 days)

- [x] Clean environment and remove dev-only shortcuts.
- [x] Lock dependencies and reproducible builds.
- [x] Split configs by `dev/staging/prod`.
- [x] Add structured logging and error tracking.

Deliverables:
- [ ] Stable local/staging setup.
- [ ] Proper CORS config per environment (strict allowlist).
- [ ] No wildcard production settings.

## Phase 1: Core Architecture (Week 1)

- [ ] Backend domain modules:
  - [ ] Auth
  - [ ] Profile
  - [ ] Astrology
  - [ ] Matching
  - [ ] Messaging
  - [ ] Billing-ready skeleton
- [ ] Database hardening:
  - [ ] Migrations
  - [ ] Constraints
  - [ ] Indexes
  - [ ] Idempotent seed scripts
- [ ] API contracts:
  - [ ] OpenAPI finalized
  - [ ] Request/response validation everywhere

Deliverables:
- [ ] Production-grade API skeleton.
- [ ] Migrations + rollback tested.

## Phase 2: Security + Compliance (Week 1-2)

- [ ] Legal docs:
  - [ ] Privacy Policy
  - [ ] Terms of Service
  - [ ] Consent language for sensitive birth data
- [ ] Consent/versioning:
  - [ ] Store policy version + timestamp + locale per user
- [ ] Data security:
  - [ ] Encryption at rest
  - [ ] TLS
  - [ ] Secrets management
- [ ] User rights:
  - [ ] Delete account/data
  - [ ] Export personal data

Deliverables:
- [ ] Release-ready legal/compliance baseline.
- [ ] Auditable consent records.

## Phase 3: Astrology Engine Quality (Week 2)

- [ ] Swiss Ephemeris accuracy validation.
- [ ] Birth data normalization:
  - [ ] Timezone confidence
  - [ ] Geocoding quality score
  - [ ] Fallback handling
- [ ] Explainability layer:
  - [ ] "Why this match" from real chart signals

Deliverables:
- [ ] Trusted astrology computation pipeline.
- [ ] Explainable match rationale API.

## Phase 4: Psychology Layer (Week 2-3)

- [ ] Build validated questionnaire set:
  - [ ] Attachment
  - [ ] Conflict style
  - [ ] Novelty/stability
  - [ ] Communication preference
- [ ] Add scoring model:
  - [ ] Normalized psych vector
  - [ ] Confidence score
- [ ] Merge into profile vector:
  - [ ] Astrology vector
  - [ ] Psych vector
  - [ ] Behavioral features

Deliverables:
- [ ] Psych profile module integrated into matching.
- [ ] Clear user-facing assessment summary.

## Phase 5: AI Matching Intelligence (Week 3-5)

- [ ] Matching system design:
  - [ ] Stage A: candidate retrieval (vector similarity / ANN index)
  - [ ] Stage B: rule-based synastry scoring
  - [ ] Stage C: AI reranker (learned weights)
- [ ] Model strategy:
  - [ ] Start with interpretable model (GBM/logistic ranking)
  - [ ] Add deep reranker if needed
- [ ] Feedback loop:
  - [ ] Like/pass/chat quality
  - [ ] Date outcome self-report
  - [ ] Long-term retention signals

Deliverables:
- [ ] Hybrid matching engine with measurable uplift.
- [ ] Offline/online evaluation metrics dashboard.

## Phase 6: UX/UI Excellence (Parallel, Week 2-6)

- [ ] Design system:
  - [ ] Typography scale
  - [ ] Color tokens
  - [ ] Spacing
  - [ ] Motion rules
- [ ] Key flows:
  - [ ] Onboarding trust
  - [ ] Assessment UX
  - [ ] Match cards
  - [ ] Explanation panels
  - [ ] Chat entry
- [ ] Accessibility:
  - [ ] Contrast
  - [ ] Readable hierarchy
  - [ ] Tap targets
  - [ ] Motion preferences

Deliverables:
- [ ] Beautiful, consistent, high-conversion interface.
- [ ] Figma + implementation parity.

## Phase 7: Messaging + Engagement (Week 5-6)

- [ ] Real-time messaging backend.
- [ ] Safety features:
  - [ ] Report/block
  - [ ] Abuse throttling
- [ ] Engagement mechanics:
  - [ ] Daily curated matches
  - [ ] Explainability cards
  - [ ] Premium feature gates

Deliverables:
- [ ] Usable social core.
- [ ] Safety and moderation baseline.

## Phase 8: Billing + Growth + Analytics (Week 6-7)

- [ ] Subscriptions + one-off report purchases.
- [ ] Event taxonomy:
  - [ ] Onboarding drop-off
  - [ ] Match-to-chat
  - [ ] Retention cohorts
  - [ ] Conversion funnel
- [ ] Experimentation framework:
  - [ ] A/B test weights and UI variants.

Deliverables:
- [ ] Revenue pipeline live.
- [ ] Decision-quality analytics.

## Phase 9: Release Engineering (Week 7-8)

- [ ] CI/CD + staged rollouts.
  - [x] 9.1 Promotion controls + release packaging baseline.
  - [x] 9.2 Staged rollout probe gate + rollback readiness drill baseline.
- [ ] Load tests + failure drills.
- [ ] Production readiness checklist:
  - [ ] SLOs
  - [ ] Backups
  - [ ] Incident runbooks
- [ ] Store submission assets + policies.

Deliverables:
- [ ] Toronto pilot launch-ready.
- [ ] Global-ready architecture retained.

---

## Psychological Questions + AI Assessment: Practical Implementation

- [ ] Questionnaire engine in onboarding.
- [ ] Responses mapped to psych factors (0-1 normalized).
- [ ] AI model consumes:
  - [ ] Astrology features
  - [ ] Psych factors
  - [ ] Behavior signals
- [ ] Output:
  - [ ] Compatibility score
  - [ ] Confidence
  - [ ] Explanation bullets
  - [ ] Uncertainty flags

Goal: intelligent matching without black-box behavior.

---

## Execution Order Starting Today

- [ ] 1. Production CORS/auth cleanup (remove dev-open behavior in release config).
- [ ] 2. Legal docs + consent versioning finalized.
- [ ] 3. Questionnaire module + psych scoring implementation.
- [ ] 4. Matching engine v1 (hybrid) + explainability responses.
- [ ] 5. UI redesign pass and polished onboarding/match flows.
