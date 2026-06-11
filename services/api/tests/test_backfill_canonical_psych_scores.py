from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.jobs.backfill_canonical_psych_scores import backfill_canonical_psycho_scores
from app.models import PsychProfile, PsychoResponse, PsychoScore, User


def test_backfill_canonical_psych_scores_is_idempotent_for_profile_backfill():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(
            User(
                id="usr-legacy",
                name="Legacy User",
                email="legacy@example.com",
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
                user_id="usr-legacy",
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
                psycho_vector=[0.6, 0.58, 0.52, 0.64, 0.4, 0.35, 0.31, 0.7, 0.25, 0.3, 0.55, 0.45, 0.72, 0.5],
                psycho_uncertainty=[0.2] * 14,
                quality_flags={},
            )
        )
        db.add(
            PsychProfile(
                user_id="usr-legacy",
                love_language="gifts",
                communication_style="direct",
                conflict_style="collaborative",
                attachment_style="secure",
                novelty_preference=0.45,
                boundaries_preference=0.72,
            )
        )
        db.commit()

        first = backfill_canonical_psycho_scores(db, user_ids=["usr-legacy"], dry_run=False)
        db.commit()
        second = backfill_canonical_psycho_scores(db, user_ids=["usr-legacy"], dry_run=False, include_canonical_v2=True)
        db.commit()

        row = db.get(PsychoScore, "usr-legacy")
        assert row is not None
        assert first[0].canonical_dimension_version == "v2_partial"
        assert second[0].canonical_dimension_version == "v2_partial"
        assert row.independence_need == 0.72
        assert row.aff_gifts == 0.75
        assert row.quality_flags["canonical_dimension_sources"]["independence_need"] == "psych_profile.boundaries_preference"
        assert row.quality_flags["canonical_dimension_sources"]["aff_gifts"] == "psych_profile.love_language"
    finally:
        db.close()


def test_backfill_prefers_response_derived_dimensions_over_profile_fallback():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(
            User(
                id="usr-response",
                name="Response User",
                email="response@example.com",
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
                user_id="usr-response",
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
                psycho_vector=[0.6, 0.58, 0.52, 0.64, 0.4, 0.35, 0.31, 0.7, 0.25, 0.3, 0.55, 0.45, 0.72, 0.5],
                psycho_uncertainty=[0.2] * 14,
                quality_flags={},
            )
        )
        db.add(
            PsychProfile(
                user_id="usr-response",
                love_language="gifts",
                communication_style="direct",
                conflict_style="collaborative",
                attachment_style="secure",
                novelty_preference=0.45,
                boundaries_preference=0.9,
            )
        )
        db.add(PsychoResponse(user_id="usr-response", item_id="ATT_09", answer=1, response_ms=1200, created_at=datetime.utcnow()))
        db.add(PsychoResponse(user_id="usr-response", item_id="AFF_03", answer=5, response_ms=1200, created_at=datetime.utcnow()))
        db.commit()

        results = backfill_canonical_psycho_scores(db, user_ids=["usr-response"], dry_run=False)
        db.commit()

        row = db.get(PsychoScore, "usr-response")
        assert row is not None
        assert results[0].status == "updated"
        assert row.independence_need == 0.0
        assert row.aff_words == 1.0
        assert row.quality_flags["canonical_dimension_sources"]["independence_need"] == "psycho_response_legacy"
        assert row.quality_flags["canonical_dimension_sources"]["aff_words"] == "psycho_response_legacy"
    finally:
        db.close()
