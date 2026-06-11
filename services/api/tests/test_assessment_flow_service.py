from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    AnalyticsEvent,
    AuthUser,
    PsychoAssessmentSession,
    PsychoDerivedPattern,
    PsychoItem,
    PsychoReport,
    PsychoScore,
    User,
    UserProfileState,
)
from app.services.assessment_flow_service import (
    build_public_progress_metadata,
    build_assessment_summary_from_session,
    finalize_assessment,
    ingest_onboarding_responses,
    replace_derived_patterns,
)


def test_assessment_flow_dual_write_summary_and_pattern_replace():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(AuthUser(id="usr-test", email="user@example.com", password_hash="hash", created_at=datetime.utcnow()))
        db.add(
            User(
                id="usr-test",
                name="Test User",
                email="user@example.com",
                birth_date="1990-01-01",
                birth_time="10:00",
                birth_place="Toronto, Canada",
                goals=["romance"],
                matching_preference="psych_behavior_astro",
                status="active",
                created_at=datetime.utcnow(),
            )
        )
        for item in (
            PsychoItem(id="B5_O_01", module="big5", prompt="p", reverse_key=False, trait_key="O", weight=1.0),
            PsychoItem(id="B5_O_02", module="big5", prompt="p", reverse_key=True, trait_key="O", weight=1.0),
            PsychoItem(id="ATT_01", module="attachment", prompt="p", reverse_key=False, trait_key="att_anxiety", weight=1.0),
            PsychoItem(id="CON_01", module="conflict", prompt="p", reverse_key=False, trait_key="conflict_direct", weight=1.0),
            PsychoItem(id="VAL_01", module="values", prompt="p", reverse_key=False, trait_key="value_stability", weight=1.0),
            PsychoItem(id="AFF_01", module="affection", prompt="p", reverse_key=False, trait_key="aff_attention", weight=1.0),
        ):
            db.add(item)
        db.commit()

        item_map = {item.id: item for item in db.query(PsychoItem).all()}
        write_result = ingest_onboarding_responses(
            db,
            user_id="usr-test",
            item_map=item_map,
            answers={
                "B5_O_01": 5,
                "B5_O_02": 1,
                "ATT_01": 4,
                "CON_01": 4,
                "VAL_01": 5,
                "AFF_01": 5,
            },
            response_ms={key: 1400 for key in item_map.keys()},
        )
        summary = build_assessment_summary_from_session(db, session_id=write_result.session.id, item_map=item_map)

        assert write_result.session.status == "completed"
        assert len(write_result.item_responses) == 6
        assert summary.legacy_traits["O"] > 0.8
        assert len(summary.derived_patterns) == 5

        replace_derived_patterns(db, user_id="usr-test", derived_patterns=summary.derived_patterns)
        replace_derived_patterns(db, user_id="usr-test", derived_patterns=summary.derived_patterns[:2])

        rows = db.query(PsychoDerivedPattern).filter(PsychoDerivedPattern.user_id == "usr-test").all()
        assert len(rows) == 2
    finally:
        db.close()


def test_finalize_assessment_updates_profile_state_and_compatibility_outputs():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(AuthUser(id="usr-test", email="user@example.com", password_hash="hash", created_at=datetime.utcnow()))
        db.add(
            User(
                id="usr-test",
                name="Test User",
                email="user@example.com",
                birth_date="1990-01-01",
                birth_time="10:00",
                birth_place="Toronto, Canada",
                goals=["romance"],
                matching_preference="psych_behavior",
                status="active",
                created_at=datetime.utcnow(),
            )
        )
        db.add(UserProfileState(user_id="usr-test"))
        for item_id, trait_key in (
            ("B5_O_01", "O"),
            ("ATT_01", "att_anxiety"),
            ("CON_01", "conflict_direct"),
            ("VAL_01", "value_stability"),
            ("AFF_01", "aff_attention"),
        ):
            db.add(PsychoItem(id=item_id, module="m", prompt="p", reverse_key=False, trait_key=trait_key, weight=1.0))
        db.commit()

        item_map = {item.id: item for item in db.query(PsychoItem).all()}
        write_result = ingest_onboarding_responses(
            db,
            user_id="usr-test",
            item_map=item_map,
            answers={"B5_O_01": 5, "ATT_01": 4, "CON_01": 4, "VAL_01": 5, "AFF_01": 5},
            response_ms={key: 1200 for key in item_map},
        )
        write_result.session.status = "in_progress"
        write_result.session.completed_at = None
        result = finalize_assessment(db, session=write_result.session, item_map=item_map)
        next_report = db.query(PsychoReport).filter(PsychoReport.user_id == "usr-test").first()

        assert result.session.status == "completed"
        assert db.get(PsychoScore, "usr-test") is not None
        assert db.query(PsychoReport).filter(PsychoReport.user_id == "usr-test").count() == 1
        assert next_report is not None
        assert next_report.session_id == write_result.session.id
        event_names = {row.event_name for row in db.query(AnalyticsEvent).filter(AnalyticsEvent.user_id == "usr-test").all()}
        assert "psychology_assessment_completed" in event_names
        assert "psychology_report_generated" in event_names
        assert "psychology_profile_updated" in event_names
        assert "psychology_compatibility_refresh_requested" in event_names
        state = db.get(UserProfileState, "usr-test")
        assert state is not None
        assert state.psycho_complete is True
        assert state.psycho_completion == 1.0
        assert state.stage == "calibrating"
    finally:
        db.close()


def test_finalize_assessment_persists_expanded_canonical_psych_dimensions():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(AuthUser(id="usr-test", email="user@example.com", password_hash="hash", created_at=datetime.utcnow()))
        db.add(
            User(
                id="usr-test",
                name="Test User",
                email="user@example.com",
                birth_date="1990-01-01",
                birth_time="10:00",
                birth_place="Toronto, Canada",
                goals=["romance"],
                matching_preference="psych_behavior",
                status="active",
                created_at=datetime.utcnow(),
            )
        )
        db.add(UserProfileState(user_id="usr-test"))
        item_defs = (
            ("B5_O_01", "O"),
            ("ATT_01", "att_anxiety"),
            ("ATT_07", "reassurance_need"),
            ("ATT_10", "independence_need"),
            ("ATT_12", "vulnerability_comfort"),
            ("CON_01", "conflict_direct"),
            ("REG_01", "emotional_regulation"),
            ("VAL_01", "value_stability"),
            ("VAL_05", "value_novelty"),
            ("AFF_01", "aff_attention"),
            ("AFF_03", "aff_touch"),
            ("AFF_05", "aff_words"),
            ("AFF_07", "aff_acts"),
            ("AFF_09", "aff_gifts"),
        )
        for item_id, trait_key in item_defs:
            db.add(PsychoItem(id=item_id, module="m", prompt="p", reverse_key=False, trait_key=trait_key, weight=1.0))
        db.commit()

        item_map = {item.id: item for item in db.query(PsychoItem).all()}
        write_result = ingest_onboarding_responses(
            db,
            user_id="usr-test",
            item_map=item_map,
            answers={
                "B5_O_01": 5,
                "ATT_01": 4,
                "ATT_07": 5,
                "ATT_10": 2,
                "ATT_12": 4,
                "CON_01": 4,
                "REG_01": 5,
                "VAL_01": 5,
                "VAL_05": 2,
                "AFF_01": 5,
                "AFF_03": 4,
                "AFF_05": 5,
                "AFF_07": 4,
                "AFF_09": 3,
            },
        )
        write_result.session.status = "in_progress"
        write_result.session.completed_at = None
        finalize_assessment(db, session=write_result.session, item_map=item_map)

        score = db.get(PsychoScore, "usr-test")
        assert score is not None
        assert score.reassurance_need > 0.5
        assert score.independence_need < 0.5
        assert score.vulnerability_comfort > 0.5
        assert score.emotional_regulation > 0.5
        assert score.aff_touch > 0.5
        assert score.aff_words > 0.5
        assert score.aff_acts > 0.5
        assert score.aff_gifts >= 0.5
        assert score.quality_flags["canonical_dimension_version"] == "v2"
    finally:
        db.close()


def test_public_progress_metadata_stays_privacy_safe_and_bounded():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(AuthUser(id="usr-test", email="user@example.com", password_hash="hash", created_at=datetime.utcnow()))
        db.add(
            PsychoAssessmentSession(
                id="pas-test",
                user_id="usr-test",
                assessment_mode="standard",
                status="awaiting_followup",
                version="v3",
                started_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
        )
        db.add(PsychoItem(id="B5_O_01", module="m", prompt="p", reverse_key=False, trait_key="O", weight=1.0))
        db.add(PsychoItem(id="FUP_ATT_01", module="m", prompt="p", reverse_key=False, trait_key="att_anxiety", weight=1.0, item_type="followup_likert"))
        db.commit()

        standard_item = db.get(PsychoItem, "B5_O_01")
        followup_item = db.get(PsychoItem, "FUP_ATT_01")
        progress_start = build_public_progress_metadata(db, session=db.get(PsychoAssessmentSession, "pas-test"), next_item=standard_item)
        progress_followup = build_public_progress_metadata(db, session=db.get(PsychoAssessmentSession, "pas-test"), next_item=followup_item)

        assert progress_start.phase in {"standard", "clarification"}
        assert progress_start.step_index >= 1
        assert progress_followup.is_followup is True
        assert progress_followup.phase == "clarification"
        assert 0.0 <= progress_followup.progress_ratio <= 1.0
        assert progress_followup.remaining_steps_hint >= 0
    finally:
        db.close()
