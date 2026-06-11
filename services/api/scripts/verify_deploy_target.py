import argparse
import sys

import requests


REQUIRED_OPENAPI_PATHS = [
    "/health/live",
    "/health/ready",
    "/health/jobs",
    "/v1/legal/consent",
    "/v1/legal/export-data",
    "/v1/legal/delete-account",
    "/v1/matches",
    "/v1/advisor",
]


def _get_json(base_url: str, path: str, timeout: float) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    response = requests.get(url, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"{path} returned {response.status_code}: {response.text}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} did not return a JSON object")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify deployed SoulMatch API target")
    parser.add_argument("--base-url", required=True, help="API base url, e.g. https://api.soulmatch.app")
    parser.add_argument("--timeout", type=float, default=6.0, help="HTTP timeout in seconds")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    timeout = args.timeout

    live = _get_json(base_url, "/health/live", timeout)
    ready = _get_json(base_url, "/health/ready", timeout)
    jobs = _get_json(base_url, "/health/jobs", timeout)
    openapi = _get_json(base_url, "/openapi.json", timeout)

    if ready.get("status") != "ok":
        raise RuntimeError(f"/health/ready is not ok: {ready}")
    checks = ready.get("checks") or {}
    if not checks.get("database") or not checks.get("startup"):
        raise RuntimeError(f"/health/ready checks failed: {checks}")

    paths = openapi.get("paths") or {}
    missing = [path for path in REQUIRED_OPENAPI_PATHS if path not in paths]
    if missing:
        raise RuntimeError(f"openapi missing required paths: {missing}")

    print(
        {
            "ok": True,
            "base_url": base_url,
            "live_status": live.get("status"),
            "ready_status": ready.get("status"),
            "jobs_count": len(jobs.get("jobs", [])),
            "verified_paths": len(REQUIRED_OPENAPI_PATHS),
        }
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[verify-deploy-target] failed: {exc}")
        sys.exit(1)
