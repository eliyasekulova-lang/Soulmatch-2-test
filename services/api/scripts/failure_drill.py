import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests


def _health_ok(base_url: str, timeout: float) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/health/ready"
    try:
        response = requests.get(url, timeout=timeout)
    except requests.RequestException as exc:
        return False, f"request_error: {exc}"
    if response.status_code != 200:
        return False, f"status_{response.status_code}"
    payload = response.json()
    if payload.get("status") != "ok":
        return False, f"ready_status={payload.get('status')}"
    checks = payload.get("checks") or {}
    if not checks.get("database") or not checks.get("startup"):
        return False, f"checks={checks}"
    return True, "ok"


def _verify_target(base_url: str, timeout: float) -> tuple[bool, str]:
    cmd = [
        sys.executable,
        "-m",
        "scripts.verify_deploy_target",
        "--base-url",
        base_url,
        "--timeout",
        str(timeout),
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode == 0:
        return True, "ok"
    return False, (result.stdout or result.stderr).strip()[-400:]


def _artifacts_exist(project_root: Path) -> tuple[bool, list[str]]:
    required = [
        project_root / "artifacts" / "releases" / "release-manifest.json",
        project_root / "artifacts" / "releases" / "promotion-decision.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    return len(missing) == 0, missing


def main() -> None:
    parser = argparse.ArgumentParser(description="Run rollback readiness failure drill checks")
    parser.add_argument("--primary-url", required=True, help="Current production/staging URL")
    parser.add_argument("--rollback-url", required=True, help="Last known-good rollback URL")
    parser.add_argument("--timeout", type=float, default=3.0, help="HTTP timeout in seconds")
    parser.add_argument(
        "--require-primary-failure",
        action="store_true",
        help="Require that primary target is unhealthy (for active outage drill)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    primary_ok, primary_reason = _health_ok(args.primary_url, args.timeout)
    rollback_health_ok, rollback_health_reason = _health_ok(args.rollback_url, args.timeout)
    rollback_verify_ok, rollback_verify_reason = _verify_target(args.rollback_url, args.timeout)
    artifacts_ok, missing_artifacts = _artifacts_exist(project_root)

    reasons: list[str] = []
    if args.require_primary_failure and primary_ok:
        reasons.append("primary is healthy while require_primary_failure was set")
    if not rollback_health_ok:
        reasons.append(f"rollback /health/ready failed: {rollback_health_reason}")
    if not rollback_verify_ok:
        reasons.append(f"rollback verify_deploy_target failed: {rollback_verify_reason}")
    if not artifacts_ok:
        reasons.append(f"missing release artifacts: {missing_artifacts}")

    ok = len(reasons) == 0
    payload = {
        "ok": ok,
        "evaluated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "primary": {"url": args.primary_url.rstrip("/"), "healthy": primary_ok, "reason": primary_reason},
        "rollback": {
            "url": args.rollback_url.rstrip("/"),
            "ready_healthy": rollback_health_ok,
            "ready_reason": rollback_health_reason,
            "verify_target_ok": rollback_verify_ok,
            "verify_target_reason": rollback_verify_reason,
        },
        "artifacts_ok": artifacts_ok,
        "reasons": reasons,
        "manual_actions": [
            "Shift traffic to rollback target",
            "Run health checks on rollback target",
            "Open incident and attach release artifacts",
        ],
    }
    print(json.dumps(payload, indent=2))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
