from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import AnalyticsEvent, PsychProfile, PsychoResponse, PsychoScore, User
from app.services.psychology_migration_report_service import (
    PsychologyMigrationThresholds,
    build_psychology_migration_report,
    emit_psychology_migration_report_event,
    evaluate_psychology_cutover_readiness,
)


def test_build_psychology_migration_report_aggregates_canonical_and_fallback_counts():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        for user_id in ("usr-v2", "usr-partial", "usr-profile", "usr-legacy"):
            db.add(
                User(
                    id=user_id,
                    name=user_id,
                    email=f"{user_id}@example.com",
                    birth_date="1990-01-01",
                    birth_time="10:00",
                    birth_place="Toronto, Canada",
                    goals=["romance"],
                    matching_preference="psych_behavior",
                    status="active",
                    created_at=datetime.utcnow(),
                )
            )
        db.add(
            PsychoScore(
                user_id="usr-v2",
                o=0.6,
                c=0.58,
                e=0.52,
                a=0.64,
                n=0.4,
                att_anxiety=0.35,
                att_avoid=0.31,
                reassurance_need=0.55,
                independence_need=0.44,
                vulnerability_comfort=0.66,
                conflict_direct=0.7,
                conflict_avoid=0.25,
                conflict_delay=0.3,
                emotional_regulation=0.74,
                value_stability=0.55,
                value_novelty=0.45,
                aff_attention=0.72,
                aff_touch=0.61,
                aff_words=0.68,
                aff_acts=0.57,
                aff_gifts=0.33,
                psycho_vector=[0.6] * 14,
                psycho_uncertainty=[0.2] * 14,
                quality_flags={
                    "canonical_dimension_version": "v2",
                    "canonical_dimensions": [
                        "reassurance_need",
                        "independence_need",
                        "vulnerability_comfort",
                        "emotional_regulation",
                        "aff_touch",
                        "aff_words",
                        "aff_acts",
                        "aff_gifts",
                    ],
                },
            )
        )
        db.add(
            PsychoScore(
                user_id="usr-partial",
                o=0.6,
                c=0.58,
                e=0.52,
                a=0.64,
                n=0.4,
                att_anxiety=0.35,
                att_avoid=0.31,
                conflict_direct=0.7,
                conflict_avoid=0.25,
                conflict_delay=0.3,
                value_stability=0.55,
                value_novelty=0.45,
                aff_attention=0.72,
                psycho_vector=[0.6] * 14,
                psycho_uncertainty=[0.2] * 14,
                quality_flags={
                    "canonical_dimension_version": "v2_partial",
                    "canonical_dimensions": ["independence_need", "aff_gifts"],
                },
            )
        )
        db.add(PsychProfile(user_id="usr-profile", boundaries_preference=0.72, novelty_preference=0.45))
        db.add(PsychoResponse(user_id="usr-legacy", item_id="ATT_09", answer=3, response_ms=1100, created_at=datetime.utcnow()))
        db.commit()

        report = build_psychology_migration_report(db)

        assert report.total_users == 4
        assert report.real_users == 4
        assert report.synthetic_users == 0
        assert report.users_with_psycho_score == 2
        assert report.users_v2 == 1
        assert report.users_v2_partial == 1
        assert report.real_users_v2 == 1
        assert report.real_users_v2_partial == 1
        assert report.users_requiring_psych_profile_fallback == 1
        assert report.users_requiring_legacy_psycho_response_backfill == 1
        assert report.matching_source_breakdown["canonical"] == 1
        assert report.matching_source_breakdown["canonical_partial"] == 1
        assert report.matching_source_breakdown["psych_profile_fallback"] == 1
        assert report.matching_source_breakdown["missing"] == 1
        assert report.missing_dimension_counts["reassurance_need"] >= 1
        assert report.readiness.psych_profile_cutover_ready is False
        assert report.readiness.psycho_response_retirement_ready is False
        assert report.readiness.low_volume_mode is True
        assert report.readiness.readiness_status == "not_ready_due_to_low_volume"
    finally:
        db.close()


def test_evaluate_psychology_cutover_readiness_honors_thresholds():
    readiness = evaluate_psychology_cutover_readiness(
        total_users=100,
        real_users=100,
        synthetic_users=0,
        users_v2_partial=3,
        users_requiring_psych_profile_fallback=1,
        users_requiring_legacy_psycho_response_backfill=0,
        synthetic_users_v2=0,
        synthetic_users_v2_partial=0,
        synthetic_users_requiring_psych_profile_fallback=0,
        synthetic_users_requiring_legacy_psycho_response_backfill=0,
        psycho_response_write_paths=[],
        thresholds=PsychologyMigrationThresholds(
            max_v2_partial_ratio=0.05,
            max_profile_fallback_ratio=0.02,
            max_legacy_backfill_ratio=0.01,
            min_real_users_for_cutover=50,
            min_synthetic_users_for_prelaunch_validation=4,
            require_zero_psycho_response_write_paths=True,
        ),
    )

    assert readiness.readiness_status == "ready_for_real_cutover"
    assert readiness.psych_profile_cutover_ready is True
    assert readiness.psycho_response_retirement_ready is True
    assert readiness.production_cutover_evaluable is True
    assert readiness.blockers == []


def test_evaluate_psychology_cutover_readiness_allows_prelaunch_validation_for_seeded_low_volume():
    readiness = evaluate_psychology_cutover_readiness(
        total_users=6,
        real_users=0,
        synthetic_users=6,
        users_v2_partial=0,
        users_requiring_psych_profile_fallback=0,
        users_requiring_legacy_psycho_response_backfill=0,
        synthetic_users_v2=6,
        synthetic_users_v2_partial=0,
        synthetic_users_requiring_psych_profile_fallback=0,
        synthetic_users_requiring_legacy_psycho_response_backfill=0,
        psycho_response_write_paths=["app.domains.onboarding.submit"],
        thresholds=PsychologyMigrationThresholds(
            min_real_users_for_cutover=50,
            min_synthetic_users_for_prelaunch_validation=4,
        ),
    )

    assert readiness.low_volume_mode is True
    assert readiness.prelaunch_validation_ready is True
    assert readiness.production_cutover_evaluable is False
    assert readiness.readiness_status == "ready_for_prelaunch_validation"
    assert readiness.psych_profile_cutover_ready is False
    assert readiness.psycho_response_retirement_ready is False


def test_emit_psychology_migration_report_event_persists_internal_events():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        report = build_psychology_migration_report(db)
        emit_psychology_migration_report_event(db, report)
        db.commit()

        event_names = [row.event_name for row in db.query(AnalyticsEvent).all()]
        assert "psychology_canonical_coverage_reported" in event_names
        assert any(name in {"psychology_cutover_ready", "psychology_cutover_not_ready"} for name in event_names)
    finally:
        db.close()
