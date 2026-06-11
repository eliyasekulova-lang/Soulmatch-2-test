# Go-Live Checklist

This checklist is ordered so self-serve/no-spend work comes first. Paid infra expansion and legal review come later.

## Phase 1: Self-Serve Hardening
- [x] Keep `services/api/STAGING_RUNBOOK.md` current.
- [x] Keep `services/api/scripts/run_local_trial.sh` noise-free and usable.
- [x] Document all required env vars and current staging defaults.
- [ ] Decide fallback behavior for low match counts.
- [ ] Run a clean staging smoke after every deploy-affecting change.
- [x] Keep a release checklist in the repo and actually use it.

## Phase 2: Low-Cost Operational Readiness
- [x] Add error monitoring (for example Sentry).
- [x] Configure deploy failure and app error alerts.
- [x] Document backup/restore steps for Render Postgres.
- [x] Test one app rollback.
- [x] Test one migration rollback on staging.
- [x] Store secrets in a password manager.
- [x] Document secret rotation.

## Phase 3: Production Infrastructure
- [ ] Create separate production Postgres.
- [ ] Create separate production web service.
- [ ] Set production env vars.
- [ ] Set production pre-deploy command to `alembic upgrade head`.
- [ ] Seed production legal docs.
- [ ] Seed production psycho items if the app depends on them.
- [ ] Connect production domain and verify HTTPS.
- [ ] Run production smoke before any public launch.

## Phase 4: Safety and Operations
- [ ] Define report/block/moderation operations.
- [ ] Define account deletion handling.
- [ ] Define support process.
- [x] Keep `services/api/INCIDENT_CHECKLIST.md` current and usable.
- [ ] Decide how to handle too-few-candidate situations.
- [ ] Decide how to handle low-confidence match quality.

## Phase 5: Legal Review
- [ ] Lawyer-review privacy policy.
- [ ] Lawyer-review terms of service.
- [ ] Review AI disclosure wording.
- [ ] Review consent language for inferred/sensitive data.
- [ ] Review deletion and retention policy.
- [ ] Review age/minor policy.

## Phase 6: Launch
- [ ] Closed beta with real testers.
- [ ] Fix onboarding and matching issues found in beta.
- [ ] Verify analytics funnel.
- [ ] Rotate launch secrets one final time.
- [ ] Run final production smoke.
- [ ] Public launch.
