import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


def _parse_created_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def evaluate_manifest(
    manifest: dict,
    now_utc: datetime,
    max_age_hours: int,
    require_release_gate: bool,
    require_deploy_verify: bool,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    created_at = _parse_created_at(manifest.get("created_at_utc"))
    if created_at is None:
        reasons.append("manifest missing valid created_at_utc")
    else:
        max_age = timedelta(hours=max_age_hours)
        if now_utc - created_at > max_age:
            reasons.append(
                f"manifest too old: created_at_utc={manifest.get('created_at_utc')} max_age_hours={max_age_hours}"
            )

    git = manifest.get("git") or {}
    if not git.get("commit_sha"):
        reasons.append("manifest missing git.commit_sha")

    database = manifest.get("database") or {}
    if not database.get("alembic_version"):
        reasons.append("manifest missing database.alembic_version")

    gates = manifest.get("gates") or {}
    if require_release_gate:
        release_gate = gates.get("release_gate") or {}
        if not release_gate.get("ran"):
            reasons.append("release_gate was not executed")
        elif not release_gate.get("ok"):
            reasons.append("release_gate did not pass")

    if require_deploy_verify:
        deploy_verify = gates.get("deploy_verify") or {}
        if not deploy_verify.get("ran"):
            reasons.append("verify_deploy_target was not executed")
        elif not deploy_verify.get("ok"):
            reasons.append("verify_deploy_target did not pass")

    return len(reasons) == 0, reasons


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate release promotion controls from manifest evidence")
    parser.add_argument("--manifest", required=True, help="Path to release manifest JSON")
    parser.add_argument("--max-age-hours", type=int, default=24, help="Maximum manifest age in hours")
    parser.add_argument(
        "--skip-release-gate-requirement",
        action="store_true",
        help="Allow promotion evaluation without requiring release_gate evidence",
    )
    parser.add_argument(
        "--skip-deploy-verify-requirement",
        action="store_true",
        help="Allow promotion evaluation without requiring verify_deploy_target evidence",
    )
    parser.add_argument(
        "--decision-output",
        default="artifacts/releases/promotion-decision.json",
        help="Where to write promotion decision JSON",
    )
    parser.add_argument("--release-owner", required=True, help="Release owner identifier")
    parser.add_argument("--legal-signoff", required=True, help="Legal signoff reference (ticket or document id)")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    now_utc = datetime.now(UTC)
    allowed, reasons = evaluate_manifest(
        manifest=manifest,
        now_utc=now_utc,
        max_age_hours=args.max_age_hours,
        require_release_gate=not args.skip_release_gate_requirement,
        require_deploy_verify=not args.skip_deploy_verify_requirement,
    )

    decision = {
        "ok": allowed,
        "evaluated_at_utc": now_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "release_id": manifest.get("release_id"),
        "manifest_path": str(manifest_path),
        "release_owner": args.release_owner,
        "legal_signoff": args.legal_signoff,
        "reasons": reasons,
    }

    decision_path = Path(args.decision_output)
    if not decision_path.is_absolute():
        decision_path = Path(__file__).resolve().parents[1] / decision_path
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    decision_path.write_text(json.dumps(decision, indent=2), encoding="utf-8")
    print(decision)
    if not allowed:
        sys.exit(1)


if __name__ == "__main__":
    main()
