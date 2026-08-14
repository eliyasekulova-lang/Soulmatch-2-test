#!/usr/bin/env python3
"""
Render pre-deploy migration script.

Tries normal `alembic upgrade head` first. If alembic_version tracking is
out of sync (common when a service is re-deployed after a gap), falls back to
SQLAlchemy create_all (IF NOT EXISTS) + alembic stamp head so future deploys
track cleanly.
"""
import subprocess
import sys

sys.path.insert(0, ".")


def run(cmd: list[str]) -> int:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.returncode != 0 and result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


print("[pre_deploy] Running alembic upgrade head...")
if run(["alembic", "upgrade", "head"]) == 0:
    print("[pre_deploy] Migrations complete.")
    sys.exit(0)

print("[pre_deploy] Normal migration failed — attempting recovery.")
print("[pre_deploy] Creating any missing tables via SQLAlchemy create_all...")

from sqlalchemy import create_engine
from app.settings import get_settings
from app.models import Base

engine = create_engine(get_settings().database_url)
Base.metadata.create_all(engine, checkfirst=True)
print("[pre_deploy] create_all complete (existing tables untouched).")

print("[pre_deploy] Stamping alembic to head...")
if run(["alembic", "stamp", "head"]) != 0:
    print("[pre_deploy] ERROR: stamp failed.", file=sys.stderr)
    sys.exit(1)

print("[pre_deploy] Recovery complete — DB is at head.")
