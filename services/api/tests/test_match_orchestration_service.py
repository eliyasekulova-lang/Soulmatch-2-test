from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import BehaviorFeature, MatchV2, PsychProfile, PsychoDerivedPattern, PsychoScore, User, UserProfileState
from app.services.match_orchestration_service import compute_orchestrated_matches, replace_match_v2_rows


def test_match_orchestration_produces_shared_ranked_rows_and_structured_dynamics():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        for user_id in ("usr-source", "usr-best", "usr-risky"):
            db.add(
                User(
                    id=user_id,
                    name=user_id,
                    email=None,
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
                UserProfileState(
                    user_id=user_id,
                    stage="eligible",
                    psycho_complete=True,
                    required_modules_complete=True,
                    quality_pass=True,
                    psycho_completion=1.0,
                    behavior_completion=1.0,
                    psycho_confidence=0.85 if user_id != "usr-risky" else 0.4,
                    behavior_confidence=0.8,
                    overall_confidence=0.8,
                )
            )
        db.add_all(
            [
                PsychoScore(
                    user_id="usr-source",
                    o=0.62,
                    c=0.58,
                    e=0.55,
                    a=0.64,
                    n=0.38,
                    att_anxiety=0.34,
                    att_avoid=0.28,
                    reassurance_need=0.6,
                    independence_need=0.4,
                    vulnerability_comfort=0.7,
                    conflict_direct=0.73,
                    conflict_avoid=0.24,
                    conflict_delay=0.25,
                    emotional_regulation=0.76,
                    value_stability=0.57,
                    value_novelty=0.43,
                    aff_attention=0.74,
                    aff_touch=0.62,
                    aff_words=0.71,
                    aff_acts=0.58,
                    aff_gifts=0.35,
                    psycho_vector=[0.62, 0.58, 0.55, 0.64, 0.38, 0.34, 0.28, 0.73, 0.24, 0.25, 0.57, 0.43, 0.74, 0.5],
                    psycho_uncertainty=[0.12] * 14,
                    quality_flags={"canonical_dimension_version": "v2"},
                ),
                PsychoScore(
                    user_id="usr-best",
                    o=0.61,
                    c=0.57,
                    e=0.53,
                    a=0.62,
                    n=0.4,
                    att_anxiety=0.36,
                    att_avoid=0.3,
                    reassurance_need=0.58,
                    independence_need=0.42,
                    vulnerability_comfort=0.68,
                    conflict_direct=0.71,
                    conflict_avoid=0.22,
                    conflict_delay=0.28,
                    emotional_regulation=0.74,
                    value_stability=0.56,
                    value_novelty=0.44,
                    aff_attention=0.7,
                    aff_touch=0.6,
                    aff_words=0.69,
                    aff_acts=0.57,
                    aff_gifts=0.34,
                    psycho_vector=[0.61, 0.57, 0.53, 0.62, 0.4, 0.36, 0.3, 0.71, 0.22, 0.28, 0.56, 0.44, 0.7, 0.5],
                    psycho_uncertainty=[0.14] * 14,
                    quality_flags={"canonical_dimension_version": "v2"},
                ),
                PsychoScore(
                    user_id="usr-risky",
                    o=0.6,
                    c=0.55,
                    e=0.5,
                    a=0.58,
                    n=0.62,
                    att_anxiety=0.78,
                    att_avoid=0.72,
                    reassurance_need=0.8,
                    independence_need=0.74,
                    vulnerability_comfort=0.28,
                    conflict_direct=0.31,
                    conflict_avoid=0.77,
                    conflict_delay=0.74,
                    emotional_regulation=0.3,
                    value_stability=0.3,
                    value_novelty=0.7,
                    aff_attention=0.4,
                    aff_touch=0.32,
                    aff_words=0.35,
                    aff_acts=0.38,
                    aff_gifts=0.7,
                    psycho_vector=[0.6, 0.55, 0.5, 0.58, 0.62, 0.78, 0.72, 0.31, 0.77, 0.74, 0.3, 0.7, 0.4, 0.5],
                    psycho_uncertainty=[0.46] * 14,
                    quality_flags={"canonical_dimension_version": "v2", "straight_lining": True},
                ),
            ]
        )
        for user_id in ("usr-source", "usr-best", "usr-risky"):
            db.add(
                BehaviorFeature(
                    user_id=user_id,
                    response_consistency=0.7,
                    response_delay_var=0.3,
                    initiative_ratio=0.5,
                    conversation_balance=0.55,
                    engagement_stability=0.68,
                    boundary_respect=0.82,
                    emotional_variability=0.4,
                    behavior_vector=[0.68, 0.72, 0.48, 0.56, 0.69, 0.81] if user_id != "usr-risky" else [0.42, 0.34, 0.72, 0.4, 0.45, 0.58],
                    behavior_uncertainty=[0.2] * 6,
                )
            )
        for user_id, key, score in (
            ("usr-source", "relational_security_profile", 0.74),
            ("usr-source", "conflict_repair_style", 0.76),
            ("usr-source", "intimacy_pace", 0.66),
            ("usr-best", "relational_security_profile", 0.72),
            ("usr-best", "conflict_repair_style", 0.74),
            ("usr-best", "intimacy_pace", 0.64),
            ("usr-risky", "relational_security_profile", 0.28),
            ("usr-risky", "conflict_repair_style", 0.24),
            ("usr-risky", "intimacy_pace", 0.22),
        ):
            db.add(
                PsychoDerivedPattern(
                    user_id=user_id,
                    pattern_key=key,
                    pattern_score=score,
                    confidence=0.8 if user_id != "usr-risky" else 0.45,
                    contributing_dimensions={},
                    explanation_internal="internal",
                )
            )
        db.commit()

        rows = compute_orchestrated_matches(
            db,
            user_id="usr-source",
            mode="romance",
            match_mode="destiny",
            candidate_ids=["usr-best", "usr-risky"],
        )

        assert len(rows) == 2
        assert rows[0].other_user_id == "usr-best"
        assert rows[0].rank_score > rows[1].rank_score
        assert rows[0].dynamics_payload["source_a"] == "canonical"
        assert rows[0].dynamics_payload["source_b"] == "canonical"
        assert rows[0].compatibility_score != rows[0].rank_score
        assert rows[0].highlights
        assert "att_anxiety" not in str(rows[0].explanation)
        assert "debug" not in str(rows[0].explanation).lower()

        created = replace_match_v2_rows(db, user_id="usr-source", rows=rows, top_k=2)
        db.commit()

        stored_rows = db.query(MatchV2).filter(MatchV2.user_id == "usr-source").order_by(MatchV2.final_score.desc()).all()
        assert created == 2
        assert stored_rows[0].compatibility_score == rows[0].compatibility_score
        assert stored_rows[0].final_score == rows[0].rank_score
    finally:
        db.close()


def test_match_orchestration_allows_profile_only_fallback_when_psycho_score_is_missing():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        for user_id in ("usr-profile-source", "usr-profile-candidate"):
            db.add(
                User(
                    id=user_id,
                    name=user_id,
                    email=None,
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
                UserProfileState(
                    user_id=user_id,
                    stage="eligible",
                    psycho_complete=True,
                    required_modules_complete=True,
                    quality_pass=True,
                    psycho_completion=1.0,
                    behavior_completion=1.0,
                    psycho_confidence=0.6,
                    behavior_confidence=0.75,
                    overall_confidence=0.7,
                )
            )
        db.add(
            PsychProfile(
                user_id="usr-profile-source",
                ocean_vector=[0.6, 0.58, 0.52, 0.64, 0.4],
                love_language="quality_time",
                communication_style="direct",
                conflict_style="collaborative",
                attachment_style="secure",
                novelty_preference=0.45,
                boundaries_preference=0.42,
            )
        )
        db.add(
            PsychProfile(
                user_id="usr-profile-candidate",
                ocean_vector=[0.61, 0.57, 0.5, 0.62, 0.42],
                love_language="quality_time",
                communication_style="direct",
                conflict_style="collaborative",
                attachment_style="secure",
                novelty_preference=0.47,
                boundaries_preference=0.4,
            )
        )
        for user_id in ("usr-profile-source", "usr-profile-candidate"):
            db.add(
                BehaviorFeature(
                    user_id=user_id,
                    response_consistency=0.7,
                    response_delay_var=0.3,
                    initiative_ratio=0.5,
                    conversation_balance=0.55,
                    engagement_stability=0.68,
                    boundary_respect=0.82,
                    emotional_variability=0.4,
                    behavior_vector=[0.68, 0.72, 0.48, 0.56, 0.69, 0.81],
                    behavior_uncertainty=[0.2] * 6,
                )
            )
        db.commit()

        rows = compute_orchestrated_matches(
            db,
            user_id="usr-profile-source",
            mode="romance",
            match_mode="destiny",
            candidate_ids=["usr-profile-candidate"],
        )

        assert len(rows) == 1
        assert rows[0].dynamics_payload["source_a"] == "psych_profile_fallback"
        assert rows[0].dynamics_payload["source_b"] == "psych_profile_fallback"
        assert rows[0].rank_score > 0
    finally:
        db.close()
