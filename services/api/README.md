# SoulMatch API (Compliance-First)

## Stack
- FastAPI + PostgreSQL + SQLAlchemy + Alembic
- DB-polled background workers for export/deletion/retention (v1)

## Module Structure
- `app/modules/policy`
- `app/modules/consent`
- `app/modules/messaging`
- `app/modules/media`
- `app/modules/moderation`
- `app/modules/rights`
- `app/modules/audit`

## Key Compliance Capabilities
- Versioned policy model by locale + jurisdiction + platform.
- Immutable consent event capture with timestamp, IP, user-agent, app version, locale, country.
- Rights workflows: export/delete/correct/restrict/withdraw.
- Deletion jobs for user-initiated account deletion.
- Backup eventual deletion semantics recorded in rights resolution payload.
- Vendor processor register and legal-basis mapping endpoints.
- Moderation report queue + admin actions + critical escalation playbook.
- Append-only audit logs (`audit_logs`) and request-level `audit_events` middleware capture.

## Workers
- `python -m scripts.process_rights_jobs`
- `python -m scripts.process_deletion_jobs`
- `python -m scripts.process_retention_jobs`
- `python -m scripts.process_behavior_profiles`
- `python -m scripts.process_safety_risk`
- `python -m scripts.process_billing_reconciliation`

Worker runs now update `job_run_telemetry` for readiness and operations visibility.

## OpenAPI YAML
- Generate with: `python -m scripts.export_openapi_yaml`
- Output: `services/api/openapi.yaml`

## Security Baseline
- Auth and rights rate limiting.
- Identity-aware auth throttling (IP + email).
- Refresh-token endpoint-specific throttling.
- Per-user message send burst throttling.
- RBAC-protected admin routes.
- Admin email allowlist enforcement in staging/production.
- Input validation via Pydantic.
- Secrets only through environment variables.
- TLS assumed at edge/load balancer.
- Strict environment validation:
  - no wildcard CORS in staging/production
  - https-only CORS origins in staging/production
  - localhost CORS origins forbidden in staging/production
  - minimum JWT secret length enforced in staging/production

## Environment Profiles
- Development: `.env.development.example`
- Staging: `.env.staging.example`
- Production: `.env.production.example`

Validate config before start:
- `python -m scripts.validate_runtime_config`

CI-safe runtime smoke check:
- `python -m scripts.smoke_runtime_health`

Release gate (all critical checks):
- `python -m scripts.release_gate`

Post-deploy target verification:
- `python -m scripts.verify_deploy_target --base-url https://api.your-domain.tld`

## Health Endpoints
- `GET /health/live` (process liveness + startup snapshot)
- `GET /health/ready` (startup + database readiness)
- `GET /health/jobs` (job telemetry + structured critical-route error counters)

## Account Deletion Compliance
- In-app deletion trigger is available through rights endpoint.
- Web deletion URL metadata exposed through `/v1/compliance/app-store`.
- Active-system deletion + backup eventual purge model is documented and auditable.

## Legal
All legal/policy text is draft and marked attorney-review-required before public launch.

## Release Checklist
- `python -m scripts.release_gate` passes.
- `python -m scripts.validate_runtime_config` passes.
- `python -m scripts.smoke_runtime_health` passes.
- `python -m pytest -q` passes.
- `GET /health/live`, `GET /health/ready`, `GET /health/jobs` return HTTP 200 in runtime.
- `python -m scripts.verify_deploy_target --base-url <prod-api-url>` passes against deployed target.
- `alembic upgrade head` applied cleanly in target environment.
- `python -m scripts.release_package --run-release-gate --verify-base-url <prod-api-url>` creates release evidence manifest.
- `python -m scripts.promotion_control --manifest artifacts/releases/release-manifest.json --release-owner <owner> --legal-signoff <ticket-or-doc-id>` returns `ok: true`.


## Billing Reliability
- Provider webhooks are replay-safe and enforce status transition rules.
- `GET /v1/billing/reconciliation` exposes admin reconciliation signals:
  - missing subscriptions for succeeded payments
  - orphan active subscriptions without succeeded payments
  - duplicate provider event ids

## Analytics Taxonomy and Funnel
- `POST /v1/events` accepts canonical event names plus `custom_*`.
- Canonical taxonomy is exposed at `GET /v1/analytics/taxonomy`.
- Funnel baseline is exposed at `GET /v1/analytics/funnel?window_days=30` for authenticated users.

## Experiments Baseline
- Sticky variant assignment endpoint: `POST /v1/experiments/assign`.
- Assignment persistence table: `experiment_assignments`.
- First assignment writes `experiment_exposure` analytics event.

## Growth Reporting Baseline
- Admin retention cohorts: `GET /v1/admin/analytics/retention?window_days=30`
- Admin KPI snapshot: `GET /v1/admin/analytics/kpis?window_days=30`
- Admin anomaly feed: `GET /v1/admin/analytics/anomalies?window_days=7`

## Local End-to-End Trial
- Run: `bash scripts/run_local_trial.sh`
- Flow covered:
  - signup
  - legal consent
  - profile creation
  - `409 profile_incomplete` gate before identity onboarding
  - `POST /v1/onboarding/submit`
  - `GET /v1/matches` returning a top-7 sorted list
- Optional overrides:
  - `BASE_URL=http://127.0.0.1:8010`
  - `EMAIL=your-test-email@example.com`
  - `PASSWORD=StrongPass#2026`

## Phase A Operational Run
- Local/CI-style operational pass:
  - `bash scripts/run_phase_a_operational.sh`
- This runs:
  - alembic upgrade -> downgrade -1 -> upgrade head
  - targeted identity integration suite
  - repeated release gate runs
- Optional runtime/staging verification:
  - `BASE_URL=https://api.your-staging.tld bash scripts/run_phase_a_operational.sh`
- Useful overrides:
  - `PYTHON_BIN=/path/to/python`
  - `DATABASE_URL=sqlite:///./phase_a_operational.db`
  - `REPEAT_RELEASE_GATE=3`
  - `TIMEOUT=6`

## Phase 9.1 Promotion Controls
- Build release evidence:
  - `python -m scripts.release_package --run-release-gate --verify-base-url http://127.0.0.1:8010 --timeout 3`
- Evaluate promotion controls:
  - `python -m scripts.promotion_control --manifest artifacts/releases/release-manifest.json --release-owner <owner> --legal-signoff <ticket-or-doc-id>`
- Offline/manual override options (for detached builds): `--commit-sha`, `--branch`, `--tag-at-head`, `--alembic-version`.

## Staging Operations
- Repeatable staging initialization and verification steps live in `services/api/STAGING_RUNBOOK.md`.
- Use this after fresh DB creation, secret rotation, or staging rebuilds.

## Go-Live Planning
- Ordered launch preparation checklist lives in `services/api/GO_LIVE_CHECKLIST.md`.
- The checklist is intentionally ordered so self-serve work comes before paid infra/legal steps.

## Phase 9.2 Staged Rollout + Failure Drill
- Canary/staged rollout probe gate:
  - `python -m scripts.staged_rollout_check --base-url http://127.0.0.1:8010 --iterations 20 --interval-seconds 1 --timeout 3`
- Rollback readiness/failure drill:
  - `python -m scripts.failure_drill --primary-url http://127.0.0.1:8010 --rollback-url http://127.0.0.1:8010 --timeout 3`
