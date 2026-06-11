# Deployment and CI/CD

## API workflow
- File: `.github/workflows/api-ci-cd.yml`
- CI gate on PR/push executes `python -m scripts.release_gate`.
- Deploy step (main branch only) triggers production deploy hook via `API_DEPLOY_HOOK_URL`.

## Mobile workflow
- File: `.github/workflows/mobile-eas.yml`
- Builds iOS and Android with EAS on `main` changes or manual dispatch.
- Optional store submission when workflow-dispatch input `submit=true`.

## Required GitHub secrets
- `API_DEPLOY_HOOK_URL`
- `EXPO_TOKEN`
- `PROD_API_BASE_URL`

## Required runtime env (API)
- `APP_ENV` (`development|test|staging|production`)
- `DATABASE_URL`
- `JWT_SECRET`
- `PII_ENCRYPTION_KEY`
- `APP_SUPPORT_EMAIL`
- `APP_POLICY_BASE_URL`
- `APP_ACCOUNT_DELETE_URL`
- `ADMIN_EMAILS`
- `CORS_ALLOW_ORIGINS` (comma-separated allowlist)
- `JWT_ACCESS_EXPIRE_MINUTES` (optional, default `30`)
- `JWT_REFRESH_EXPIRE_DAYS` (optional, default `30`)
- `AUTH_RATE_LIMIT_PER_MINUTE` (optional, default `25`)
- `AUTH_REFRESH_RATE_LIMIT_PER_MINUTE` (optional, default `15`)
- `MESSAGE_SEND_RATE_LIMIT_PER_MINUTE` (optional, default `30`)
- `LOG_LEVEL` (optional, default `INFO`)
- `SENTRY_DSN` (optional, recommended for staging/prod)
- `SENTRY_ENVIRONMENT` (optional, defaults to `APP_ENV`)
- `SEED_DEMO_CANDIDATES` (optional)
- `EPHE_PATH` (optional)

## Go/No-Go Deployment Gates
All must pass before a production release:
1. `python -m scripts.release_gate`
2. `alembic upgrade head`
3. Deployed target check:
   - `python -m scripts.verify_deploy_target --base-url <api-url>`
4. Release package and promotion decision:
   - `python -m scripts.release_package --run-release-gate --verify-base-url <api-url>`
   - `python -m scripts.promotion_control --manifest artifacts/releases/release-manifest.json --release-owner <owner> --legal-signoff <ticket-or-doc-id>`
5. Staged rollout gate:
   - `python -m scripts.staged_rollout_check --base-url <api-url>`
6. Manual legal/compliance gate:
   - legal docs marked attorney-reviewed for release scope
   - support + account deletion URLs reachable from production app metadata

## Deployment Sequence (Production)
1. Merge approved PR to `main`.
2. Confirm CI `release_gate` job passes.
3. Execute migration on production database:
   - `alembic upgrade head`
4. Trigger deploy:
   - via `API_DEPLOY_HOOK_URL` (workflow deploy step) or approved infra trigger.
5. Run post-deploy verification:
   - `python -m scripts.verify_deploy_target --base-url <api-url>`
6. Build release package and evaluate promotion controls:
   - `python -m scripts.release_package --run-release-gate --verify-base-url <api-url>`
   - `python -m scripts.promotion_control --manifest artifacts/releases/release-manifest.json --release-owner <owner> --legal-signoff <ticket-or-doc-id>`
7. Run staged rollout check:
   - `python -m scripts.staged_rollout_check --base-url <api-url>`
8. Record release audit evidence:
   - commit SHA, migration revision, verification output, deployment timestamp.

## Rollback Procedure
Use when post-deploy verification or critical SLOs fail.
1. Stop rollout / remove traffic from new revision.
2. Rollback app deployment to last known-good artifact.
3. Validate `/health/live`, `/health/ready`, `/health/jobs` on rollback target.
4. If migration must be reversed, perform only reviewed downgrade step:
   - `alembic downgrade -1`
   - never execute downgrade without data impact review.
5. Open incident entry and attach evidence:
   - failing checks
   - rollback timestamp
   - owner + next action
6. Run rollback readiness drill against fallback:
   - `python -m scripts.failure_drill --primary-url <api-url> --rollback-url <rollback-api-url>`
