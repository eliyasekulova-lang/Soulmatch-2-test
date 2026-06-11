#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
DB_URL="${DATABASE_URL:-sqlite:///./phase_a_operational.db}"
APP_ENV_VALUE="${APP_ENV:-test}"
REPEAT_RELEASE_GATE="${REPEAT_RELEASE_GATE:-3}"
BASE_URL="${BASE_URL:-}"
TIMEOUT="${TIMEOUT:-6}"

echo "[phase-a] python=$PYTHON_BIN"
echo "[phase-a] app_env=$APP_ENV_VALUE"
echo "[phase-a] database_url=$DB_URL"
echo "[phase-a] repeat_release_gate=$REPEAT_RELEASE_GATE"

export APP_ENV="$APP_ENV_VALUE"
export DATABASE_URL="$DB_URL"
export ADMIN_EMAILS="${ADMIN_EMAILS:-admin@example.com}"
export AUTH_RATE_LIMIT_PER_MINUTE="${AUTH_RATE_LIMIT_PER_MINUTE:-10000}"
export AUTH_REFRESH_RATE_LIMIT_PER_MINUTE="${AUTH_REFRESH_RATE_LIMIT_PER_MINUTE:-10000}"
export MESSAGE_SEND_RATE_LIMIT_PER_MINUTE="${MESSAGE_SEND_RATE_LIMIT_PER_MINUTE:-10000}"
export JWT_SECRET="${JWT_SECRET:-dev-only-change-me}"
export PII_ENCRYPTION_KEY="${PII_ENCRYPTION_KEY:-dev-only-pii-key-change-me}"
export APP_SUPPORT_EMAIL="${APP_SUPPORT_EMAIL:-support@soulmatch.app}"
export APP_POLICY_BASE_URL="${APP_POLICY_BASE_URL:-https://soulmatch.app/legal}"
export APP_ACCOUNT_DELETE_URL="${APP_ACCOUNT_DELETE_URL:-https://soulmatch.app/account/delete}"

echo "[phase-a] step=migration_smoke"
"$PYTHON_BIN" -m alembic upgrade head
"$PYTHON_BIN" -m alembic downgrade -1
"$PYTHON_BIN" -m alembic upgrade head

echo "[phase-a] step=identity_suite"
"$PYTHON_BIN" -m scripts.run_identity_tests

echo "[phase-a] step=release_gate_repeat"
for run in $(seq 1 "$REPEAT_RELEASE_GATE"); do
  echo "[phase-a] release_gate_run=$run"
  "$PYTHON_BIN" -m scripts.release_gate
done

if [[ -n "$BASE_URL" ]]; then
  echo "[phase-a] step=deploy_verify base_url=$BASE_URL"
  "$PYTHON_BIN" -m scripts.verify_deploy_target --base-url "$BASE_URL" --timeout "$TIMEOUT"
  echo "[phase-a] step=runtime_smoke base_url=$BASE_URL"
  BASE_URL="$BASE_URL" PYTHON_BIN="$PYTHON_BIN" bash ./scripts/run_local_trial.sh
fi

echo "[phase-a] ok=true"
