#!/usr/bin/env bash
# start.sh — Render production startup script
# Runs DB migrations then starts the API with gunicorn.
set -euo pipefail

echo "[start] Running database migrations..."
alembic upgrade head

echo "[start] Seeding legal docs and policy defaults..."
# These are idempotent — safe to run on every deploy
python -c "
import os, sys
sys.path.insert(0, '.')
os.environ.setdefault('APP_ENV', 'production')
from app.database import SessionLocal, init_db
from app.domains.legal import seed_legal_documents
from app.domains.compliance import seed_default_policies, seed_default_policy_versions, seed_default_compliance_registers
from app.jobs.seed_psycho_items import seed_psycho_items
init_db()
with SessionLocal() as db:
    seed_default_policies(db)
    seed_default_policy_versions(db)
    seed_default_compliance_registers(db)
    seed_legal_documents(db)
    seed_psycho_items(db)
print('[start] Seeding complete.')
"

echo "[start] Starting gunicorn..."
exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "${GUNICORN_WORKERS:-2}" \
  --bind "0.0.0.0:${PORT:-8000}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
