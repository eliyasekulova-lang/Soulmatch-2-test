import os

from fastapi.testclient import TestClient

# CI/local-safe defaults. Real deployments override via environment.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./smoke_runtime_health.db")
os.environ.setdefault("SEED_DEMO_CANDIDATES", "false")

from app.database import Base, engine
from app.main import app
from app.settings import get_settings


def _assert_health_endpoint(client: TestClient, path: str) -> dict:
    response = client.get(path)
    if response.status_code != 200:
        raise RuntimeError(f"{path} returned {response.status_code}: {response.text}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} did not return a JSON object")
    return payload


def main() -> None:
    settings = get_settings()
    # Ensures runtime config validation is exercised in CI/pre-release checks.
    if settings.app_env not in {"development", "test", "staging", "production"}:
        raise RuntimeError(f"unexpected APP_ENV: {settings.app_env}")

    # Ensure startup seed/read checks run against an initialized schema in smoke mode.
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as client:
        live = _assert_health_endpoint(client, "/health/live")
        ready = _assert_health_endpoint(client, "/health/ready")
        jobs = _assert_health_endpoint(client, "/health/jobs")

    if "uptime_state" not in live:
        raise RuntimeError("health/live missing uptime_state")
    if "checks" not in ready or "errors" not in ready:
        raise RuntimeError("health/ready missing checks/errors")
    if "jobs" not in jobs or "error_counters" not in jobs:
        raise RuntimeError("health/jobs missing jobs/error_counters")

    print(
        {
            "ok": True,
            "app_env": settings.app_env,
            "live_status": live.get("status"),
            "ready_status": ready.get("status"),
            "jobs_count": len(jobs.get("jobs", [])),
        }
    )


if __name__ == "__main__":
    main()
