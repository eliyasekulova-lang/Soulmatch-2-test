from datetime import UTC, datetime, timedelta

from scripts.promotion_control import evaluate_manifest
from scripts.release_package import build_manifest


def _base_manifest(now_utc: datetime) -> dict:
    return {
        "release_id": "rel-20260219T000000Z",
        "created_at_utc": now_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "git": {"commit_sha": "abc123"},
        "database": {"alembic_version": "20260219_000019_experiment_assignments"},
        "gates": {
            "release_gate": {"ran": True, "ok": True},
            "deploy_verify": {"ran": True, "ok": True},
        },
    }


def test_promotion_controls_pass_for_fresh_valid_manifest():
    now_utc = datetime.now(UTC)
    manifest = _base_manifest(now_utc)
    allowed, reasons = evaluate_manifest(
        manifest=manifest,
        now_utc=now_utc,
        max_age_hours=24,
        require_release_gate=True,
        require_deploy_verify=True,
    )
    assert allowed is True
    assert reasons == []


def test_promotion_controls_fail_for_old_manifest():
    now_utc = datetime.now(UTC)
    created_at = now_utc - timedelta(hours=30)
    manifest = _base_manifest(created_at)
    allowed, reasons = evaluate_manifest(
        manifest=manifest,
        now_utc=now_utc,
        max_age_hours=24,
        require_release_gate=True,
        require_deploy_verify=True,
    )
    assert allowed is False
    assert any("manifest too old" in reason for reason in reasons)


def test_release_package_uses_explicit_overrides(tmp_path):
    workspace_root = tmp_path / "workspace"
    project_root = workspace_root / "services" / "api"
    docs_dir = workspace_root / "docs"
    project_root.mkdir(parents=True)
    docs_dir.mkdir(parents=True)
    (project_root / "openapi.yaml").write_text("openapi: 3.1.0", encoding="utf-8")
    (project_root / "requirements.txt").write_text("fastapi==0.0.0", encoding="utf-8")
    (docs_dir / "RELEASE_CONTROL.md").write_text("release control", encoding="utf-8")

    manifest = build_manifest(
        project_root=project_root,
        workspace_root=workspace_root,
        run_release_gate=False,
        verify_base_url=None,
        timeout=1.0,
        commit_sha="sha-123",
        branch="main",
        tag_at_head="v1.2.3",
        alembic_version_override="20260219_000019",
    )
    assert manifest["git"]["commit_sha"] == "sha-123"
    assert manifest["database"]["alembic_version"] == "20260219_000019"
