# Release Control and Verification

Last updated: 2026-02-18

## Purpose
This document defines the minimum operational controls required before any SoulMatch API release can be promoted to production.

## Mandatory Release Gates
1. Code + runtime gates:
   - `python -m scripts.release_gate`
2. Database migration gate:
   - `alembic upgrade head`
3. Post-deploy API gate:
   - `python -m scripts.verify_deploy_target --base-url <prod-api-url>`
4. Release evidence package:
   - `python -m scripts.release_package --run-release-gate --verify-base-url <prod-api-url>`
5. Promotion control decision:
   - `python -m scripts.promotion_control --manifest artifacts/releases/release-manifest.json --release-owner <owner> --legal-signoff <ticket-or-doc-id>`
6. Compliance gate:
   - Current legal docs are attorney-reviewed for release scope.
   - Account deletion URL and policy base URL are reachable.
7. Staged rollout gate:
   - `python -m scripts.staged_rollout_check --base-url <prod-api-url>`

## Evidence to Capture Per Release
- Git commit SHA
- Alembic target revision
- Release gate output
- Deployed target verifier output
- Release manifest JSON (`artifacts/releases/release-manifest.json`)
- Promotion decision JSON (`artifacts/releases/promotion-decision.json`)
- UTC deployment timestamp
- Release owner

## Blocker Conditions (No-Go)
- Any `release_gate` step fails
- `/health/ready` is not `ok` or reports failed checks
- Required OpenAPI paths missing from deployed target
- `promotion_control` output `ok` is false
- Legal/compliance sign-off missing for release scope

## Rollback Trigger Conditions
- Post-deploy verifier fails
- P1/P2 incident triggered within 60 minutes of deployment
- Elevated 5xx rates on critical routes
- Staged rollout gate returns `recommendation: hold`

## Rollback Minimum Steps
1. Shift traffic to previous stable revision.
2. Validate health endpoints on rollback target.
3. If required and reviewed, run controlled migration rollback.
4. Open incident record and attach rollback evidence.
5. Run rollback readiness drill output capture:
   - `python -m scripts.failure_drill --primary-url <prod-api-url> --rollback-url <rollback-api-url>`
