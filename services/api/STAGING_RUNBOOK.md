# Staging Runbook

This runbook is for the Render staging environment backing `https://soulmatching-staging.onrender.com`.

## Preconditions
- Render web service is live.
- Render Postgres is reachable.
- `Pre-Deploy Command` is set to `alembic upgrade head`.
- Local shell is using Python 3.11 when running API tooling.

## Environment Setup
From `services/api`:

```bash
python3.11 -m venv /tmp/soulmatch-api-venv
source /tmp/soulmatch-api-venv/bin/activate
pip install -r requirements.txt
```

Notes:
- Keep the venv outside the repository path if your workspace path contains `:`. Python refuses to create virtualenvs inside such paths.
- `./scripts/setup_test_env.sh --python "$(which python3.11)" --venv /tmp/soulmatch-api-venv` is the supported shortcut for local validation setup.

Export staging values before running DB or seed commands:

```bash
export APP_ENV=staging
export DATABASE_URL='RENDER_EXTERNAL_DATABASE_URL'
export JWT_SECRET='STAGING_JWT_SECRET_AT_LEAST_32_CHARS'
export PII_ENCRYPTION_KEY='STAGING_PII_KEY_AT_LEAST_32_CHARS'
export ADMIN_EMAILS='ops@example.com'
export CORS_ALLOW_ORIGINS='https://staging.soulmatch.app,https://staging-admin.soulmatch.app'
export APP_SUPPORT_EMAIL='support@soulmatch.app'
export APP_POLICY_BASE_URL='https://staging.soulmatch.app/legal'
export APP_ACCOUNT_DELETE_URL='https://staging.soulmatch.app/account/delete'
export BASE_URL='https://soulmatching-staging.onrender.com'
```

## Migration Smoke
Run this from `services/api`:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Expected result: all three commands complete without SQLAlchemy or runtime config errors.

For the full psychology validation stack in a provisioned environment:

```bash
/tmp/soulmatch-api-venv/bin/python -m scripts.run_psychology_validation --database-url "$DATABASE_URL"
```

Notes:
- The validation runner requires a PostgreSQL `DATABASE_URL` for Alembic smoke, backfill dry-run, and migration-state reporting.
- If `DATABASE_URL` is omitted, the runner falls back to a temporary SQLite database and only executes the pytest-safe portion of the validation flow.
- For low-volume prelaunch validation, you can seed deterministic synthetic canonical users before the report stage:

```bash
/tmp/soulmatch-api-venv/bin/python -m scripts.run_psychology_validation --database-url "$DATABASE_URL" --seed-synthetic-users --synthetic-user-count 6
```

- This validates canonical psychology coverage in staging/testing without treating seeded users as proof of production cutover readiness.

## Synthetic Canonical Coverage
To seed deterministic synthetic psychology users directly:

```bash
/tmp/soulmatch-api-venv/bin/python -m app.jobs.seed_canonical_psych_test_users --database-url "$DATABASE_URL" --limit 6
```

These users are clearly marked as synthetic/test data and are intended for staging or test environments only.

## Staging Seed Initialization
Seed legal docs:

```bash
PYTHONPATH=. python -m scripts.seed_legal_docs
```

Seed psycho items:

```bash
PYTHONPATH=. python - <<'PY'
from app.database import SessionLocal
from app.jobs.seed_psycho_items import seed_psycho_items

db = SessionLocal()
try:
    created = seed_psycho_items(db)
    print(f"psycho_items_seeded created={created}")
finally:
    db.close()
PY
```

Notes:
- `legal_documents_seeded` is acceptable even if documents already exist.
- `psycho_items_seeded created=0` is acceptable if items were already seeded.

## Final No-Noise Verification
From `services/api`:

```bash
export EMAIL="verify$(date +%s)@example.com"
export PASSWORD='StrongPass#2026'
```

Signup and capture auth:

```bash
SIGNUP=$(curl -sS -X POST "$BASE_URL/v1/auth/signup" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"birth_date\":\"1997-06-20\"}")
export TOKEN=$(printf "%s" "$SIGNUP" | python -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
export USER_ID=$(printf "%s" "$SIGNUP" | python -c 'import sys,json; print(json.load(sys.stdin)["user_id"])')
echo "$SIGNUP"
```

Legal consent:

```bash
curl -sS -X POST "$BASE_URL/v1/legal/consent" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"accept":true}'
echo
```

Create profile:

```bash
curl -sS -X POST "$BASE_URL/v1/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"id\":\"$USER_ID\",\"name\":\"Verify User\",\"email\":\"$EMAIL\",\"birth\":{\"date\":\"1997-06-20\",\"time\":\"09:30\",\"place\":\"Toronto, Canada\",\"latitude\":43.6532,\"longitude\":-79.3832,\"timezone\":\"America/Toronto\"},\"goals\":[\"romance\",\"friendship\"],\"consent_privacy\":true,\"consent_sensitive_data\":true,\"policy_version\":\"v1\"}"
echo
```

Pre-onboarding gate should return HTTP `409`:

```bash
curl -i -sS "$BASE_URL/v1/matches" -H "Authorization: Bearer $TOKEN"
```

Submit onboarding:

```bash
curl -sS -X POST "$BASE_URL/v1/onboarding/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"birth":{"birth_date":"1997-06-20","birth_time":"09:30:00","birth_place_name":"Toronto, Canada","lat":43.6532,"lon":-79.3832,"timezone_iana":"America/Toronto","birth_datetime_utc":"1997-06-20T13:30:00Z","dst_flag":true},"psycho":{"answers":{"B5_O_01":2,"B5_O_02":3,"B5_O_03":4,"B5_O_04":5,"B5_C_01":1,"B5_C_02":2,"B5_C_03":3,"B5_C_04":4,"B5_E_01":5,"B5_E_02":1,"B5_E_03":2,"B5_E_04":3,"B5_A_01":4,"B5_A_02":5,"B5_A_03":1,"B5_A_04":2,"B5_N_01":3,"B5_N_02":4,"B5_N_03":5,"B5_N_04":1,"ATT_01":2,"ATT_02":3,"ATT_03":4,"ATT_04":5,"CON_01":1,"CON_02":2,"CON_03":3,"VAL_01":4,"VAL_02":5,"AFF_01":1},"response_ms":{"B5_O_01":1400,"B5_O_02":1400,"B5_O_03":1400,"B5_O_04":1400,"B5_C_01":1400,"B5_C_02":1400,"B5_C_03":1400,"B5_C_04":1400,"B5_E_01":1400,"B5_E_02":1400,"B5_E_03":1400,"B5_E_04":1400,"B5_A_01":1400,"B5_A_02":1400,"B5_A_03":1400,"B5_A_04":1400,"B5_N_01":1400,"B5_N_02":1400,"B5_N_03":1400,"B5_N_04":1400,"ATT_01":1400,"ATT_02":1400,"ATT_03":1400,"ATT_04":1400,"CON_01":1400,"CON_02":1400,"CON_03":1400,"VAL_01":1400,"VAL_02":1400,"AFF_01":1400}}}'
echo
```

Fetch matches after onboarding:

```bash
curl -sS "$BASE_URL/v1/matches" -H "Authorization: Bearer $TOKEN"
echo
```

Expected result:
- pre-onboarding call returns `409 profile_incomplete`
- onboarding returns `stage: eligible`
- post-onboarding matches call returns a JSON list

## Secret Rotation
Rotate these if they are ever exposed in terminal, chat, screenshots, or logs:
- Render Postgres credential / `DATABASE_URL`
- `JWT_SECRET`
- `PII_ENCRYPTION_KEY`

Rotation order:
1. create new DB credential in Render Postgres
2. update web service `DATABASE_URL`
3. rotate `JWT_SECRET`
4. rotate `PII_ENCRYPTION_KEY`
5. redeploy service
6. rerun the final verification flow

## Render Postgres Backup and Restore
- Render Postgres recovery and logical exports are managed from the database `Recovery` page.
- Paid Render Postgres plans support point-in-time recovery (PITR).
- PITR creates a new database instance from an earlier timestamp so you can validate it before switching traffic.

### Recovery Drill
1. Open `soulmatch-staging-db` in Render.
2. Open the `Recovery` page.
3. Confirm PITR is available.
4. Create a logical export and verify it appears in the export list.
5. If doing a full restore drill, click `Restore Database`, choose a test timestamp, and create a new recovery instance.
6. Validate the recovered database before switching any service to it.
7. If the restore is only a drill, delete the recovery instance after validation.

### Switching To A Recovered Database
1. Copy the recovered database `External Database URL`.
2. Update the web service `DATABASE_URL`.
3. Redeploy the web service.
4. Re-run staging verification.

Notes:
- Render recommends PITR over restoring from an export for recent data loss.
- Deleting a database permanently removes its retained backups.

## Error Monitoring
Sentry is already wired in the API application startup through `init_sentry(settings.sentry_dsn, settings.sentry_environment)`.

### Required Environment Variables
Add these in Render when you are ready to enable Sentry:

- `SENTRY_DSN=YOUR_SENTRY_DSN`
- `SENTRY_ENVIRONMENT=staging`

Notes:
- Leaving `SENTRY_DSN` empty disables Sentry.
- `SENTRY_ENVIRONMENT` should be `staging` for the staging service and `production` for the production service.

### Staging Enablement
1. Open Render service `soulmatching-staging`.
2. Go to `Environment`.
3. Confirm `SENTRY_DSN` is set.
4. Confirm `SENTRY_ENVIRONMENT=staging`.
5. Save and deploy if you changed anything.
6. Trigger one handled test error or review the next real error in Sentry.

### Verification
After deploy, confirm:
- app still passes `/health/live`
- app still passes `/health/ready`
- a test exception appears in Sentry with environment `staging`
