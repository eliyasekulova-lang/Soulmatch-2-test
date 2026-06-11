from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import tempfile
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TESTS = [
    "tests/test_backfill_canonical_psych_scores.py",
    "tests/test_seed_canonical_psych_test_users.py",
    "tests/test_psychology_migration_report_service.py",
    "tests/test_run_psychology_validation.py",
    "tests/test_compatibility_dynamics_service.py",
    "tests/test_match_orchestration_service.py",
    "tests/test_assessment_flow_service.py",
    "tests/test_integration.py::test_canonical_backfill_updates_partial_rows_and_preserves_rank_vs_compatibility_scores",
    "tests/test_integration.py::test_recompute_matches_supports_profile_only_fallback_users",
]


@dataclass(frozen=True)
class ValidationStepResult:
    name: str
    status: str
    detail: str
    exit_code: int


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _run(cmd: list[str], *, env: dict[str, str]) -> int:
    print("[psychology-validation] running:", " ".join(cmd))
    return subprocess.run(cmd, env=env, check=False).returncode


def _alembic_cmd(py_bin: str, *args: str) -> list[str]:
    return [
        py_bin,
        "-c",
        "from alembic.config import main; import sys; sys.exit(main(argv=sys.argv[1:]))",
        *args,
    ]


def _base_env(db_url: str) -> dict[str, str]:
    env = os.environ.copy()
    env["APP_ENV"] = "test"
    env["DATABASE_URL"] = db_url
    env["ADMIN_EMAILS"] = "admin@example.com"
    env["AUTH_RATE_LIMIT_PER_MINUTE"] = "10000"
    env["AUTH_REFRESH_RATE_LIMIT_PER_MINUTE"] = "10000"
    env["MESSAGE_SEND_RATE_LIMIT_PER_MINUTE"] = "10000"
    env["PYTHONPYCACHEPREFIX"] = "/tmp/pycache"
    return env


def _database_kind(db_url: str) -> str:
    normalized = db_url.strip().lower()
    if normalized.startswith("postgresql"):
        return "postgres"
    if normalized.startswith("sqlite"):
        return "sqlite"
    return "other"


def _resolve_database_url(explicit_db_url: str | None) -> tuple[str | None, str]:
    if explicit_db_url and explicit_db_url.strip():
        return explicit_db_url.strip(), "explicit"
    env_db_url = os.getenv("DATABASE_URL", "").strip()
    if env_db_url:
        return env_db_url, "environment"
    return None, "temporary_sqlite"


def _dependency_steps(*, skip_migrations: bool, skip_tests: bool) -> list[ValidationStepResult]:
    steps: list[ValidationStepResult] = []
    required_modules = [("sqlalchemy", False), ("alembic.config", skip_migrations), ("pytest", skip_tests)]
    for module_name, skipped in required_modules:
        step_name = f"dependency:{module_name}"
        if skipped:
            steps.append(ValidationStepResult(name=step_name, status="skip", detail="skipped by flag", exit_code=0))
            continue
        if _has_module(module_name):
            steps.append(ValidationStepResult(name=step_name, status="pass", detail="module available", exit_code=0))
        else:
            steps.append(
                ValidationStepResult(
                    name=step_name,
                    status="fail",
                    detail="missing dependency; run `python -m pip install -r requirements.txt`",
                    exit_code=2,
                )
            )
    return steps


def _run_alembic_smoke(py_bin: str, db_url: str) -> ValidationStepResult:
    if _database_kind(db_url) != "postgres":
        return ValidationStepResult(
            name="alembic:smoke",
            status="skip",
            detail="project Alembic smoke requires a PostgreSQL DATABASE_URL; SQLite temp databases cannot render PostgreSQL-only types such as JSONB",
            exit_code=0,
        )
    env = _base_env(db_url)
    for label, cmd in (
        ("upgrade", _alembic_cmd(py_bin, "-c", "alembic.ini", "upgrade", "head")),
        ("downgrade", _alembic_cmd(py_bin, "-c", "alembic.ini", "downgrade", "-1")),
        ("re-upgrade", _alembic_cmd(py_bin, "-c", "alembic.ini", "upgrade", "head")),
    ):
        rc = _run(cmd, env=env)
        if rc != 0:
            return ValidationStepResult(name=f"alembic:{label}", status="fail", detail=f"{label} failed", exit_code=rc)
    return ValidationStepResult(name="alembic:smoke", status="pass", detail="upgrade/downgrade/re-upgrade passed", exit_code=0)


def _run_backfill_dry_run(py_bin: str, db_url: str) -> ValidationStepResult:
    env = _base_env(db_url)
    rc = _run([py_bin, "-m", "app.jobs.backfill_canonical_psych_scores", "--dry-run", "--limit", "5"], env=env)
    if rc != 0:
        return ValidationStepResult(name="backfill:dry-run", status="fail", detail="dry-run failed", exit_code=rc)
    return ValidationStepResult(name="backfill:dry-run", status="pass", detail="dry-run completed", exit_code=0)


def _run_migration_report(py_bin: str, db_url: str) -> ValidationStepResult:
    env = _base_env(db_url)
    rc = _run([py_bin, "-m", "scripts.report_psychology_migration_state", "--database-url", db_url], env=env)
    if rc != 0:
        return ValidationStepResult(name="migration-report", status="fail", detail="report command failed", exit_code=rc)
    return ValidationStepResult(name="migration-report", status="pass", detail="report command completed", exit_code=0)


def _run_synthetic_seed(py_bin: str, db_url: str, seed_count: int) -> ValidationStepResult:
    env = _base_env(db_url)
    rc = _run(
        [py_bin, "-m", "app.jobs.seed_canonical_psych_test_users", "--database-url", db_url, "--limit", str(seed_count)],
        env=env,
    )
    if rc != 0:
        return ValidationStepResult(name="seed:synthetic-canonical-users", status="fail", detail="synthetic seed failed", exit_code=rc)
    return ValidationStepResult(name="seed:synthetic-canonical-users", status="pass", detail=f"seeded {seed_count} synthetic canonical users", exit_code=0)


def _run_pytest(py_bin: str, db_url: str, tests: list[str], extra_args: list[str]) -> ValidationStepResult:
    env = _base_env(db_url)
    rc = _run([py_bin, "-m", "pytest", "-q", *tests, *extra_args], env=env)
    if rc != 0:
        return ValidationStepResult(name="pytest:targeted", status="fail", detail="targeted pytest failed", exit_code=rc)
    return ValidationStepResult(name="pytest:targeted", status="pass", detail="targeted pytest passed", exit_code=0)


def _print_summary(results: list[ValidationStepResult]) -> None:
    print("[psychology-validation] summary")
    for result in results:
        print(f"  - {result.name}: {result.status} ({result.detail})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run migration, backfill, coverage report, and targeted test validation for the psychology engine.")
    parser.add_argument("--python", dest="python_bin", default=sys.executable, help="Python binary to use.")
    parser.add_argument("--skip-migrations", action="store_true", help="Skip Alembic smoke validation.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest validation.")
    parser.add_argument("--skip-report", action="store_true", help="Skip migration-state report execution.")
    parser.add_argument("--seed-synthetic-users", action="store_true", help="Seed deterministic synthetic canonical users before report validation.")
    parser.add_argument("--synthetic-user-count", type=int, default=4, help="Number of synthetic canonical users to seed when --seed-synthetic-users is enabled.")
    parser.add_argument(
        "--database-url",
        help="Database URL for Alembic/backfill/report validation. Defaults to DATABASE_URL when set; otherwise uses a temporary SQLite database for pytest-only validation.",
    )
    parser.add_argument("pytest_args", nargs="*", help="Extra args passed through to pytest.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)

    results = _dependency_steps(skip_migrations=args.skip_migrations, skip_tests=args.skip_tests)
    dependency_failures = [result for result in results if result.status == "fail"]
    if dependency_failures:
        _print_summary(results)
        return max(result.exit_code for result in dependency_failures)

    database_url, database_source = _resolve_database_url(args.database_url)
    if database_source == "temporary_sqlite":
        results.append(
            ValidationStepResult(
                name="database:url",
                status="skip",
                detail="DATABASE_URL not set; using temporary SQLite for pytest-only validation. Provide --database-url or export DATABASE_URL for PostgreSQL Alembic/report execution.",
                exit_code=0,
            )
        )
        temp_ctx = tempfile.TemporaryDirectory(prefix="soulmatch_psych_validation_")
    else:
        results.append(
            ValidationStepResult(
                name="database:url",
                status="pass",
                detail=f"using {database_source} {_database_kind(database_url or '')} database url",
                exit_code=0,
            )
        )
        temp_ctx = nullcontext(None)

    with temp_ctx as tmpdir:
        db_url = database_url or f"sqlite:///{Path(tmpdir) / 'psychology_validation.db'}"
        if args.skip_migrations:
            results.append(ValidationStepResult(name="alembic:smoke", status="skip", detail="skipped by flag", exit_code=0))
        else:
            results.append(_run_alembic_smoke(args.python_bin, db_url))

        can_run_db_steps = _database_kind(db_url) == "postgres" and results[-1].status == "pass"

        if can_run_db_steps:
            if args.seed_synthetic_users:
                results.append(_run_synthetic_seed(args.python_bin, db_url, args.synthetic_user_count))
                can_run_db_steps = results[-1].status == "pass"
            else:
                results.append(ValidationStepResult(name="seed:synthetic-canonical-users", status="skip", detail="synthetic seed not requested", exit_code=0))
        else:
            results.append(ValidationStepResult(name="seed:synthetic-canonical-users", status="skip", detail="PostgreSQL DATABASE_URL not provided", exit_code=0))

        if can_run_db_steps:
            results.append(_run_backfill_dry_run(args.python_bin, db_url))
        else:
            reason = "PostgreSQL DATABASE_URL not provided" if _database_kind(db_url) != "postgres" else "blocked by Alembic failure"
            results.append(ValidationStepResult(name="backfill:dry-run", status="skip", detail=reason, exit_code=0))

        if args.skip_report:
            results.append(ValidationStepResult(name="migration-report", status="skip", detail="skipped by flag", exit_code=0))
        elif can_run_db_steps:
            results.append(_run_migration_report(args.python_bin, db_url))
        else:
            reason = "PostgreSQL DATABASE_URL not provided" if _database_kind(db_url) != "postgres" else "blocked by Alembic failure"
            results.append(ValidationStepResult(name="migration-report", status="skip", detail=reason, exit_code=0))

        if args.skip_tests:
            results.append(ValidationStepResult(name="pytest:targeted", status="skip", detail="skipped by flag", exit_code=0))
        else:
            results.append(_run_pytest(args.python_bin, db_url, DEFAULT_TESTS, args.pytest_args))

    _print_summary(results)
    failures = [result for result in results if result.status == "fail"]
    if failures:
        return max(result.exit_code for result in failures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
