from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import AuthUser, PsychoAssessmentSession, PsychoReport
from app.services.psychology_report_service import (
    create_versioned_psychology_report,
    get_latest_psychology_report,
    get_psychology_report_history,
)


def _summary(answered_followup_item_ids: set[str] | None = None):
    return SimpleNamespace(
        scored=SimpleNamespace(
            traits={
                "O": 0.7,
                "C": 0.6,
                "E": 0.55,
                "att_anxiety": 0.45,
                "att_avoid": 0.3,
                "independence_need": 0.5,
                "conflict_delay": 0.4,
                "conflict_avoid": 0.3,
                "value_stability": 0.6,
                "value_novelty": 0.45,
                "aff_attention": 0.7,
                "aff_touch": 0.4,
                "aff_words": 0.5,
                "aff_acts": 0.6,
                "aff_gifts": 0.2,
            },
            scoring_metadata={"answered_item_count": 24},
            quality_flags={"reflection_score": 0.5},
        ),
        contradiction_summary=SimpleNamespace(meaningful_tensions=[]),
        derived_patterns=[],
        answered_followup_item_ids=answered_followup_item_ids or set(),
        session=SimpleNamespace(id="pas-test"),
    )


def test_report_service_creates_versioned_reports_and_returns_latest():
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
                status="completed",
                version="v3",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
        )
        db.commit()

        first = create_versioned_psychology_report(db, user_id="usr-test", summary=_summary())
        second = create_versioned_psychology_report(db, user_id="usr-test", summary=_summary({"FUP_ATT_01"}))

        reports = db.query(PsychoReport).filter(PsychoReport.user_id == "usr-test").order_by(PsychoReport.id.asc()).all()
        assert len(reports) == 2
        assert first.report_version == "r1"
        assert second.report_version == "r2"
        assert first.session_id == "pas-test"
        assert get_latest_psychology_report(db, user_id="usr-test").report_version == "r2"
        assert [report.report_version for report in get_psychology_report_history(db, user_id="usr-test")] == ["r2", "r1"]
    finally:
        db.close()
