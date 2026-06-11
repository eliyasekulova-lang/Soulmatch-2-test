from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalyticsEvent, PsychProfile, PsychoResponse, PsychoScore, User

from ..jobs.backfill_canonical_psych_scores import CANONICAL_V2_DIMENSIONS


# Explicit operational inventory used for cutover reporting. These lists are
# intentionally maintained in code so retirement decisions stay auditable.
PSYCHO_RESPONSE_READ_PATHS = [
    "app.services.psychology_response_adapter.adapt_legacy_psycho_responses",
    "app.jobs.backfill_canonical_psych_scores._load_best_response_bundle",
]

PSYCHO_RESPONSE_WRITE_PATHS: list[str] = []

PSYCH_PROFILE_FALLBACK_PATHS = [
    "app.services.compatibility_dynamics_service.build_matching_psych_data",
    "app.services.match_orchestration_service.compute_orchestrated_matches",
]


@dataclass(frozen=True)
class PsychologyMigrationThresholds:
    max_v2_partial_ratio: float = 0.10
    max_profile_fallback_ratio: float = 0.02
    max_legacy_backfill_ratio: float = 0.02
    min_real_users_for_cutover: int = 50
    min_synthetic_users_for_prelaunch_validation: int = 4
    require_zero_psycho_response_write_paths: bool = True


@dataclass(frozen=True)
class PsychologyCutoverReadiness:
    readiness_status: str
    psych_profile_cutover_ready: bool
    psycho_response_retirement_ready: bool
    low_volume_mode: bool
    sample_too_small_for_real_cutover: bool
    prelaunch_validation_ready: bool
    real_cutover_ready: bool
    production_cutover_evaluable: bool
    blockers: list[str]


@dataclass(frozen=True)
class PsychologyMigrationReport:
    total_users: int
    real_users: int
    synthetic_users: int
    users_with_psycho_score: int
    users_v2: int
    users_v2_partial: int
    users_missing_canonical_score: int
    users_requiring_psych_profile_fallback: int
    users_requiring_legacy_psycho_response_backfill: int
    users_with_psych_profile_only: int
    users_with_legacy_psycho_response: int
    real_users_v2: int
    real_users_v2_partial: int
    real_users_requiring_psych_profile_fallback: int
    real_users_requiring_legacy_psycho_response_backfill: int
    synthetic_users_v2: int
    synthetic_users_v2_partial: int
    synthetic_users_requiring_psych_profile_fallback: int
    synthetic_users_requiring_legacy_psycho_response_backfill: int
    matching_source_breakdown: dict[str, int]
    missing_dimension_counts: dict[str, int]
    psycho_response_read_paths: list[str]
    psycho_response_write_paths: list[str]
    psych_profile_fallback_paths: list[str]
    readiness: PsychologyCutoverReadiness

    @property
    def v2_ratio(self) -> float:
        return _ratio(self.users_v2, self.total_users)

    @property
    def v2_partial_ratio(self) -> float:
        return _ratio(self.users_v2_partial, self.total_users)

    @property
    def psych_profile_fallback_ratio(self) -> float:
        return _ratio(self.users_requiring_psych_profile_fallback, self.total_users)

    @property
    def legacy_backfill_ratio(self) -> float:
        return _ratio(self.users_requiring_legacy_psycho_response_backfill, self.total_users)


def build_psychology_migration_report(
    db: Session,
    *,
    thresholds: PsychologyMigrationThresholds | None = None,
) -> PsychologyMigrationReport:
    thresholds = thresholds or PsychologyMigrationThresholds()
    users = list(db.scalars(select(User).order_by(User.id)).all())
    user_ids = [user.id for user in users]
    score_rows = {row.user_id: row for row in db.scalars(select(PsychoScore)).all()}
    profile_ids = set(db.scalars(select(PsychProfile.user_id)).all())
    response_ids = set(db.scalars(select(PsychoResponse.user_id).distinct()).all())
    synthetic_user_ids = {user.id for user in users if _is_synthetic_user(user)}
    real_user_ids = set(user_ids) - synthetic_user_ids

    users_v2 = 0
    users_v2_partial = 0
    real_users_v2 = 0
    real_users_v2_partial = 0
    synthetic_users_v2 = 0
    synthetic_users_v2_partial = 0
    matching_source_breakdown: Counter[str] = Counter()
    missing_dimension_counts: Counter[str] = Counter()

    for user_id in user_ids:
        row = score_rows.get(user_id)
        if row is None:
            if user_id in profile_ids:
                matching_source_breakdown["psych_profile_fallback"] += 1
            else:
                matching_source_breakdown["missing"] += 1
            continue

        quality_flags = dict(row.quality_flags or {})
        version = quality_flags.get("canonical_dimension_version")
        canonical_dimensions = set(quality_flags.get("canonical_dimensions") or [])
        if version == "v2":
            users_v2 += 1
            if user_id in synthetic_user_ids:
                synthetic_users_v2 += 1
            else:
                real_users_v2 += 1
            matching_source_breakdown["canonical"] += 1
        else:
            users_v2_partial += 1
            if user_id in synthetic_user_ids:
                synthetic_users_v2_partial += 1
            else:
                real_users_v2_partial += 1
            matching_source_breakdown["canonical_partial"] += 1
        for dimension in CANONICAL_V2_DIMENSIONS:
            if dimension not in canonical_dimensions:
                missing_dimension_counts[dimension] += 1

    users_with_psycho_score = len(score_rows)
    users_with_psych_profile_only = sum(1 for user_id in profile_ids if user_id not in score_rows)
    users_requiring_psych_profile_fallback = users_with_psych_profile_only
    users_with_legacy_psycho_response = len(response_ids)
    real_users_requiring_psych_profile_fallback = sum(1 for user_id in real_user_ids if user_id in profile_ids and user_id not in score_rows)
    synthetic_users_requiring_psych_profile_fallback = sum(1 for user_id in synthetic_user_ids if user_id in profile_ids and user_id not in score_rows)
    users_requiring_legacy_psycho_response_backfill = sum(
        1
        for user_id in response_ids
        if (user_id not in score_rows) or (dict(score_rows[user_id].quality_flags or {}).get("canonical_dimension_version") != "v2")
    )
    real_users_requiring_legacy_psycho_response_backfill = sum(
        1
        for user_id in response_ids & real_user_ids
        if (user_id not in score_rows) or (dict(score_rows[user_id].quality_flags or {}).get("canonical_dimension_version") != "v2")
    )
    synthetic_users_requiring_legacy_psycho_response_backfill = sum(
        1
        for user_id in response_ids & synthetic_user_ids
        if (user_id not in score_rows) or (dict(score_rows[user_id].quality_flags or {}).get("canonical_dimension_version") != "v2")
    )
    users_missing_canonical_score = len(user_ids) - users_v2

    readiness = evaluate_psychology_cutover_readiness(
        total_users=len(user_ids),
        real_users=len(real_user_ids),
        synthetic_users=len(synthetic_user_ids),
        users_v2_partial=real_users_v2_partial,
        users_requiring_psych_profile_fallback=real_users_requiring_psych_profile_fallback,
        users_requiring_legacy_psycho_response_backfill=real_users_requiring_legacy_psycho_response_backfill,
        synthetic_users_v2=synthetic_users_v2,
        synthetic_users_v2_partial=synthetic_users_v2_partial,
        synthetic_users_requiring_psych_profile_fallback=synthetic_users_requiring_psych_profile_fallback,
        synthetic_users_requiring_legacy_psycho_response_backfill=synthetic_users_requiring_legacy_psycho_response_backfill,
        psycho_response_write_paths=PSYCHO_RESPONSE_WRITE_PATHS,
        thresholds=thresholds,
    )

    return PsychologyMigrationReport(
        total_users=len(user_ids),
        real_users=len(real_user_ids),
        synthetic_users=len(synthetic_user_ids),
        users_with_psycho_score=users_with_psycho_score,
        users_v2=users_v2,
        users_v2_partial=users_v2_partial,
        users_missing_canonical_score=users_missing_canonical_score,
        users_requiring_psych_profile_fallback=users_requiring_psych_profile_fallback,
        users_requiring_legacy_psycho_response_backfill=users_requiring_legacy_psycho_response_backfill,
        users_with_psych_profile_only=users_with_psych_profile_only,
        users_with_legacy_psycho_response=users_with_legacy_psycho_response,
        real_users_v2=real_users_v2,
        real_users_v2_partial=real_users_v2_partial,
        real_users_requiring_psych_profile_fallback=real_users_requiring_psych_profile_fallback,
        real_users_requiring_legacy_psycho_response_backfill=real_users_requiring_legacy_psycho_response_backfill,
        synthetic_users_v2=synthetic_users_v2,
        synthetic_users_v2_partial=synthetic_users_v2_partial,
        synthetic_users_requiring_psych_profile_fallback=synthetic_users_requiring_psych_profile_fallback,
        synthetic_users_requiring_legacy_psycho_response_backfill=synthetic_users_requiring_legacy_psycho_response_backfill,
        matching_source_breakdown=dict(matching_source_breakdown),
        missing_dimension_counts=dict(sorted(missing_dimension_counts.items(), key=lambda item: (-item[1], item[0]))),
        psycho_response_read_paths=list(PSYCHO_RESPONSE_READ_PATHS),
        psycho_response_write_paths=list(PSYCHO_RESPONSE_WRITE_PATHS),
        psych_profile_fallback_paths=list(PSYCH_PROFILE_FALLBACK_PATHS),
        readiness=readiness,
    )


def evaluate_psychology_cutover_readiness(
    *,
    total_users: int,
    real_users: int,
    synthetic_users: int,
    users_v2_partial: int,
    users_requiring_psych_profile_fallback: int,
    users_requiring_legacy_psycho_response_backfill: int,
    synthetic_users_v2: int,
    synthetic_users_v2_partial: int,
    synthetic_users_requiring_psych_profile_fallback: int,
    synthetic_users_requiring_legacy_psycho_response_backfill: int,
    psycho_response_write_paths: list[str],
    thresholds: PsychologyMigrationThresholds | None = None,
) -> PsychologyCutoverReadiness:
    thresholds = thresholds or PsychologyMigrationThresholds()
    blockers: list[str] = []
    structural_blockers: list[str] = []
    low_volume_mode = real_users < thresholds.min_real_users_for_cutover
    sample_too_small_for_real_cutover = low_volume_mode
    production_cutover_evaluable = not low_volume_mode

    evaluation_denominator = real_users if real_users > 0 else total_users
    v2_partial_ratio = _ratio(users_v2_partial, evaluation_denominator)
    profile_fallback_ratio = _ratio(users_requiring_psych_profile_fallback, evaluation_denominator)
    legacy_backfill_ratio = _ratio(users_requiring_legacy_psycho_response_backfill, evaluation_denominator)

    synthetic_validation_blockers: list[str] = []
    if synthetic_users < thresholds.min_synthetic_users_for_prelaunch_validation:
        synthetic_validation_blockers.append(
            f"synthetic_user_count={synthetic_users} below prelaunch validation minimum {thresholds.min_synthetic_users_for_prelaunch_validation}"
        )
    if synthetic_users_v2 < thresholds.min_synthetic_users_for_prelaunch_validation:
        synthetic_validation_blockers.append(
            f"synthetic_users_v2={synthetic_users_v2} below prelaunch validation minimum {thresholds.min_synthetic_users_for_prelaunch_validation}"
        )
    if synthetic_users_v2_partial > 0:
        synthetic_validation_blockers.append(f"synthetic_users_v2_partial={synthetic_users_v2_partial} remain")
    if synthetic_users_requiring_psych_profile_fallback > 0:
        synthetic_validation_blockers.append(
            f"synthetic_users_requiring_psych_profile_fallback={synthetic_users_requiring_psych_profile_fallback} remain"
        )
    if synthetic_users_requiring_legacy_psycho_response_backfill > 0:
        synthetic_validation_blockers.append(
            f"synthetic_users_requiring_legacy_psycho_response_backfill={synthetic_users_requiring_legacy_psycho_response_backfill} remain"
        )
    prelaunch_validation_ready = len(synthetic_validation_blockers) == 0

    psych_profile_cutover_ready = True
    if v2_partial_ratio > thresholds.max_v2_partial_ratio:
        psych_profile_cutover_ready = False
        structural_blockers.append(
            f"v2_partial_ratio={v2_partial_ratio:.3f} exceeds threshold {thresholds.max_v2_partial_ratio:.3f}"
        )
    if profile_fallback_ratio > thresholds.max_profile_fallback_ratio:
        psych_profile_cutover_ready = False
        structural_blockers.append(
            f"psych_profile_fallback_ratio={profile_fallback_ratio:.3f} exceeds threshold {thresholds.max_profile_fallback_ratio:.3f}"
        )

    psycho_response_retirement_ready = psych_profile_cutover_ready
    if legacy_backfill_ratio > thresholds.max_legacy_backfill_ratio:
        psycho_response_retirement_ready = False
        structural_blockers.append(
            f"legacy_backfill_ratio={legacy_backfill_ratio:.3f} exceeds threshold {thresholds.max_legacy_backfill_ratio:.3f}"
        )
    if thresholds.require_zero_psycho_response_write_paths and psycho_response_write_paths:
        psycho_response_retirement_ready = False
        structural_blockers.append("active_psycho_response_write_paths remain")

    if low_volume_mode:
        blockers.append(
            f"real_user_count={real_users} below cutover minimum {thresholds.min_real_users_for_cutover}"
        )
        psych_profile_cutover_ready = False
        psycho_response_retirement_ready = False

    if low_volume_mode and prelaunch_validation_ready:
        readiness_status = "ready_for_prelaunch_validation"
        blockers.extend(structural_blockers)
    elif low_volume_mode:
        has_seeded_prelaunch_sample = synthetic_users > 0
        readiness_status = (
            "not_ready_due_to_data_quality_or_legacy_dependency"
            if has_seeded_prelaunch_sample and synthetic_validation_blockers
            else "not_ready_due_to_low_volume"
        )
        blockers.extend(structural_blockers)
    elif psych_profile_cutover_ready and psycho_response_retirement_ready:
        readiness_status = "ready_for_real_cutover"
        blockers.extend(structural_blockers)
    else:
        readiness_status = "not_ready_due_to_data_quality_or_legacy_dependency"
        blockers.extend(structural_blockers)

    if low_volume_mode:
        blockers.extend(synthetic_validation_blockers)

    return PsychologyCutoverReadiness(
        readiness_status=readiness_status,
        psych_profile_cutover_ready=psych_profile_cutover_ready,
        psycho_response_retirement_ready=psycho_response_retirement_ready,
        low_volume_mode=low_volume_mode,
        sample_too_small_for_real_cutover=sample_too_small_for_real_cutover,
        prelaunch_validation_ready=prelaunch_validation_ready,
        real_cutover_ready=(not low_volume_mode) and psych_profile_cutover_ready and psycho_response_retirement_ready,
        production_cutover_evaluable=production_cutover_evaluable,
        blockers=blockers,
    )


def emit_psychology_migration_report_event(db: Session, report: PsychologyMigrationReport) -> None:
    db.add(
        AnalyticsEvent(
            user_id=None,
            event_name="psychology_canonical_coverage_reported",
            event_payload={
                "total_users": report.total_users,
                "users_v2": report.users_v2,
                "users_v2_partial": report.users_v2_partial,
                "real_users": report.real_users,
                "synthetic_users": report.synthetic_users,
                "users_requiring_psych_profile_fallback": report.users_requiring_psych_profile_fallback,
                "users_requiring_legacy_psycho_response_backfill": report.users_requiring_legacy_psycho_response_backfill,
                "matching_source_breakdown": report.matching_source_breakdown,
            },
        )
    )
    db.add(
        AnalyticsEvent(
            user_id=None,
            event_name="psychology_cutover_ready" if (
                report.readiness.psych_profile_cutover_ready and report.readiness.psycho_response_retirement_ready
            ) else "psychology_cutover_not_ready",
            event_payload={
                "readiness_status": report.readiness.readiness_status,
                "psych_profile_cutover_ready": report.readiness.psych_profile_cutover_ready,
                "psycho_response_retirement_ready": report.readiness.psycho_response_retirement_ready,
                "prelaunch_validation_ready": report.readiness.prelaunch_validation_ready,
                "low_volume_mode": report.readiness.low_volume_mode,
                "blockers": report.readiness.blockers,
            },
        )
    )


def _ratio(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return part / float(whole)


def _is_synthetic_user(user: User) -> bool:
    status = str(user.status or "").strip().lower()
    email = str(user.email or "").strip().lower()
    return status.startswith("synthetic") or email.endswith("@synthetic.soulmatch.test")
