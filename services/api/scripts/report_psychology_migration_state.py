from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Report canonical psychology migration coverage and cutover readiness.")
    parser.add_argument("--emit-event", action="store_true", help="Persist internal analytics events for the generated report.")
    parser.add_argument("--database-url", help="Optional database URL override for the report session.")
    parser.add_argument("--max-v2-partial-ratio", type=float, default=0.10)
    parser.add_argument("--max-profile-fallback-ratio", type=float, default=0.02)
    parser.add_argument("--max-legacy-backfill-ratio", type=float, default=0.02)
    parser.add_argument("--min-real-users-for-cutover", type=int, default=50)
    parser.add_argument("--min-synthetic-users-for-prelaunch-validation", type=int, default=4)
    args = parser.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    from app.database import SessionLocal
    from app.services.psychology_migration_report_service import (
        PsychologyMigrationThresholds,
        build_psychology_migration_report,
        emit_psychology_migration_report_event,
    )

    thresholds = PsychologyMigrationThresholds(
        max_v2_partial_ratio=args.max_v2_partial_ratio,
        max_profile_fallback_ratio=args.max_profile_fallback_ratio,
        max_legacy_backfill_ratio=args.max_legacy_backfill_ratio,
        min_real_users_for_cutover=args.min_real_users_for_cutover,
        min_synthetic_users_for_prelaunch_validation=args.min_synthetic_users_for_prelaunch_validation,
    )

    try:
        with SessionLocal() as db:
            report = build_psychology_migration_report(db, thresholds=thresholds)
            if args.emit_event:
                emit_psychology_migration_report_event(db, report)
                db.commit()
    except Exception as exc:
        print(f"Psychology Migration State Error: {exc}", file=sys.stderr)
        print(
            "Hint: export a reachable PostgreSQL DATABASE_URL (for staging or local validation) before running this report.",
            file=sys.stderr,
        )
        return 1

    print("Psychology Migration State")
    print(f"total_users={report.total_users}")
    print(f"real_users={report.real_users}")
    print(f"synthetic_users={report.synthetic_users}")
    print(f"users_with_psycho_score={report.users_with_psycho_score}")
    print(f"users_v2={report.users_v2} ({report.v2_ratio:.3f})")
    print(f"users_v2_partial={report.users_v2_partial} ({report.v2_partial_ratio:.3f})")
    print(f"real_users_v2={report.real_users_v2}")
    print(f"real_users_v2_partial={report.real_users_v2_partial}")
    print(f"synthetic_users_v2={report.synthetic_users_v2}")
    print(f"synthetic_users_v2_partial={report.synthetic_users_v2_partial}")
    print(f"users_missing_canonical_score={report.users_missing_canonical_score}")
    print(f"users_requiring_psych_profile_fallback={report.users_requiring_psych_profile_fallback} ({report.psych_profile_fallback_ratio:.3f})")
    print(f"users_requiring_legacy_psycho_response_backfill={report.users_requiring_legacy_psycho_response_backfill} ({report.legacy_backfill_ratio:.3f})")
    print(f"real_users_requiring_psych_profile_fallback={report.real_users_requiring_psych_profile_fallback}")
    print(f"real_users_requiring_legacy_psycho_response_backfill={report.real_users_requiring_legacy_psycho_response_backfill}")
    print(f"synthetic_users_requiring_psych_profile_fallback={report.synthetic_users_requiring_psych_profile_fallback}")
    print(f"synthetic_users_requiring_legacy_psycho_response_backfill={report.synthetic_users_requiring_legacy_psycho_response_backfill}")
    print(f"users_with_psych_profile_only={report.users_with_psych_profile_only}")
    print(f"users_with_legacy_psycho_response={report.users_with_legacy_psycho_response}")
    print("matching_source_breakdown=" + ",".join(f"{key}:{value}" for key, value in sorted(report.matching_source_breakdown.items())))
    print(
        "missing_dimension_counts="
        + ",".join(f"{key}:{value}" for key, value in report.missing_dimension_counts.items())
    )
    print("psycho_response_read_paths=" + ",".join(report.psycho_response_read_paths))
    print("psycho_response_write_paths=" + ",".join(report.psycho_response_write_paths))
    print("psych_profile_fallback_paths=" + ",".join(report.psych_profile_fallback_paths))
    print(f"low_volume_mode={report.readiness.low_volume_mode}")
    print(f"sample_too_small_for_real_cutover={report.readiness.sample_too_small_for_real_cutover}")
    print(f"prelaunch_validation_ready={report.readiness.prelaunch_validation_ready}")
    print(f"production_cutover_evaluable={report.readiness.production_cutover_evaluable}")
    print(f"readiness_status={report.readiness.readiness_status}")
    print(f"psych_profile_cutover_ready={report.readiness.psych_profile_cutover_ready}")
    print(f"psycho_response_retirement_ready={report.readiness.psycho_response_retirement_ready}")
    print("cutover_blockers=" + ("; ".join(report.readiness.blockers) if report.readiness.blockers else "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
