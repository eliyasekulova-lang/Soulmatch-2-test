# Incident Checklist

Use this when staging or production is failing in a way that affects deploys, auth, onboarding, matching, or availability.

## 1. Triage
- Identify affected environment: `staging` or `production`.
- Identify impact: deploy failure, startup failure, auth failure, onboarding failure, matching failure, DB failure, or elevated error rate.
- Record exact timestamp in UTC.
- Record latest commit SHA and latest Render deploy ID.

## 2. Stabilize
- Check Render service health endpoints:
  - `/health/live`
  - `/health/ready`
  - `/health/jobs`
- Check most recent Render deploy logs.
- If the latest deploy caused the issue, roll back to the last known good deploy.
- If DB or migration related, stop making further schema changes until root cause is understood.

## 3. Check Common Causes
- secret/env var drift
- bad `DATABASE_URL`
- missing `JWT_SECRET`
- missing `PII_ENCRYPTION_KEY`
- bad CORS settings
- failed migration
- missing legal docs seed
- missing psycho items seed
- expired external credential
- recent code push that changed onboarding or matching behavior

## 4. Contain
- Roll back app deploy if necessary.
- Restore previous DB connection only if credential rotation caused outage.
- Re-run staging verification after rollback or env fix.
- Avoid making multiple speculative changes at once.

## 5. Verify Recovery
- `/health/live` returns OK
- `/health/ready` returns OK
- signup works
- legal consent works
- profile creation works
- onboarding works
- matches endpoint returns expected shape

## 6. Document
Record:
- incident start time
- root cause
- user impact
- mitigation
- final fix
- follow-up tasks needed to prevent recurrence

## 7. Follow-Up
- add or update runbook steps
- add or update test coverage
- rotate secrets if exposure or credential drift was involved
- schedule any deeper cleanup that was deferred during incident response
