from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.jobs.seed_psycho_items import seed_psycho_items
from app.models import BehaviorSignalEvent, PsychoItem
from app.psychology_item_bank import PSYCHOLOGY_ITEM_BANK
from app.services.eligibility import evaluate_eligibility
from app.modules.behavior_service import compute_behavior_profile
from app.modules.moderation.service import is_critical_reason
from app.modules.policy.service import sha256_text


def test_is_critical_reason():
    assert is_critical_reason("csam") is True
    assert is_critical_reason("violent_threat") is True
    assert is_critical_reason("spam") is False


def test_sha256_text_deterministic():
    assert sha256_text("abc") == sha256_text("abc")
    assert sha256_text("abc") != sha256_text("abcd")


def test_behavior_profile_aggregation_scores():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        now = datetime.utcnow()
        for idx in range(10):
            db.add(
                BehaviorSignalEvent(
                    user_id="usr-test",
                    event_type="message_sent",
                    event_payload={
                        "reply_ms": 300000,
                        "message_length": 140 + idx,
                        "asked_question": idx % 2 == 0,
                        "read": True,
                        "replied": True,
                        "initiated": idx % 3 == 0,
                        "boundary_violation": False,
                    },
                    created_at=now - timedelta(days=min(idx, 5)),
                )
            )
        db.commit()

        profile = compute_behavior_profile(db, "usr-test", window_days=30)
        assert len(profile.behavior_vector) == 6
        assert 0 <= profile.reply_time_score <= 1
        assert profile.boundary_respect_score >= 0.9
    finally:
        db.close()


def test_eligibility_allows_psych_behavior_without_astro():
    result = evaluate_eligibility(
        astro_completion=0.0,
        psycho_completion=1.0,
        behavior_completion=1.0,
        quality_flags={},
        psycho_uncertainty_avg=0.1,
        require_astro=False,
    )
    assert result.required_modules_complete is True
    assert result.stage == "eligible"
    assert result.eligibility_score >= 0.99


def test_seed_psycho_items_uses_item_bank_and_model_defaults():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        created = seed_psycho_items(db)
        assert created == len(PSYCHOLOGY_ITEM_BANK)

        rows = db.query(PsychoItem).all()
        assert len(rows) == len(PSYCHOLOGY_ITEM_BANK)
        assert {"likert", "followup_likert"} == {row.item_type for row in rows}
        assert {row.version for row in rows} == {"v1", "v2", "v3"}
        assert all(row.is_active is True for row in rows)
        assert any(row.followup_eligible is True for row in rows)
    finally:
        db.close()
