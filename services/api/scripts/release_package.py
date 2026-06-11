import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from app.database import SessionLocal


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_value(args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _read_alembic_version() -> tuple[str | None, str | None]:
    session = SessionLocal()
    try:
        version = session.execute(text("select version_num from alembic_version")).scalar()
        return version, None
    except Exception as exc:  # pragma: no cover - environment-dependent
        return None, str(exc)
    finally:
        session.close()


def _run_step(step: str, cmd: list[str]) -> dict:
    result = subprocess.run(cmd, check=False)
    return {"step": step, "ok": result.returncode == 0, "exit_code": result.returncode}


def build_manifest(
    project_root: Path,
    workspace_root: Path,
    run_release_gate: bool,
    verify_base_url: str | None,
    timeout: float,
    commit_sha: str | None = None,
    branch: str | None = None,
    tag_at_head: str | None = None,
    alembic_version_override: str | None = None,
) -> dict:
    gates: dict[str, dict] = {
        "release_gate": {"ran": False, "ok": None, "exit_code": None},
        "deploy_verify": {"ran": False, "ok": None, "exit_code": None, "base_url": verify_base_url},
    }
    if run_release_gate:
        step = _run_step("release_gate", [sys.executable, "-m", "scripts.release_gate"])
        gates["release_gate"] = {"ran": True, **step}
    if verify_base_url:
        step = _run_step(
            "verify_deploy_target",
            [
                sys.executable,
                "-m",
                "scripts.verify_deploy_target",
                "--base-url",
                verify_base_url,
                "--timeout",
                str(timeout),
            ],
        )
        gates["deploy_verify"] = {"ran": True, "base_url": verify_base_url, **step}

    if alembic_version_override:
        alembic_version, alembic_error = alembic_version_override, None
    else:
        alembic_version, alembic_error = _read_alembic_version()
    release_id = datetime.now(UTC).strftime("rel-%Y%m%dT%H%M%SZ")
    resolved_sha = commit_sha or _git_value(["rev-parse", "HEAD"]) or None
    resolved_branch = branch or _git_value(["rev-parse", "--abbrev-ref", "HEAD"]) or None
    resolved_tag = tag_at_head or _git_value(["tag", "--points-at", "HEAD"]) or None

    return {
        "manifest_version": "v1",
        "release_id": release_id,
        "created_at_utc": _utc_now_iso(),
        "git": {
            "commit_sha": resolved_sha,
            "branch": resolved_branch,
            "tag_at_head": resolved_tag,
        },
        "database": {
            "alembic_version": alembic_version,
            "error": alembic_error,
        },
        "artifacts": {
            "openapi_yaml_sha256": _sha256_file(project_root / "openapi.yaml"),
            "requirements_sha256": _sha256_file(project_root / "requirements.txt"),
            "release_control_sha256": _sha256_file(workspace_root / "docs" / "RELEASE_CONTROL.md"),
        },
        "gates": gates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a release evidence package for SoulMatch API")
    parser.add_argument(
        "--output",
        default="artifacts/releases/release-manifest.json",
        help="Output manifest path",
    )
    parser.add_argument(
        "--run-release-gate",
        action="store_true",
        help="Run release gate and include result in manifest",
    )
    parser.add_argument(
        "--verify-base-url",
        help="If set, run deploy verifier against this base URL and include result in manifest",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=6.0,
        help="HTTP timeout for deploy verification",
    )
    parser.add_argument("--commit-sha", help="Override git commit SHA for detached or artifact builds")
    parser.add_argument("--branch", help="Override git branch for detached or artifact builds")
    parser.add_argument("--tag-at-head", help="Override git tag for detached or artifact builds")
    parser.add_argument("--alembic-version", help="Override alembic revision if DB query is unavailable")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    workspace_root = Path(__file__).resolve().parents[3]
    manifest = build_manifest(
        project_root=project_root,
        workspace_root=workspace_root,
        run_release_gate=args.run_release_gate,
        verify_base_url=args.verify_base_url,
        timeout=args.timeout,
        commit_sha=args.commit_sha,
        branch=args.branch,
        tag_at_head=args.tag_at_head,
        alembic_version_override=args.alembic_version,
    )

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = project_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print({"ok": True, "manifest_path": str(output_path), "release_id": manifest["release_id"]})


if __name__ == "__main__":
    main()
