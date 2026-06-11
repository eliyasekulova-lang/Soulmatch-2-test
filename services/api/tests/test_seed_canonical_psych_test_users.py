from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.jobs.seed_canonical_psych_test_users import (
    SYNTHETIC_TEST_EMAIL_DOMAIN,
    SYNTHETIC_TEST_USER_STATUS,
    seed_canonical_psych_test_users,
)
from app.jobs.seed_psycho_items import seed_psycho_items
from app.models import AuthUser, BehaviorFeature, PsychoDerivedPattern, PsychoReport, PsychoScore, User, UserProfileState
from app.services.psychology_migration_report_service import build_psychology_migration_report


def test_seed_canonical_psych_test_users_creates_v2_canonical_artifacts():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        seed_psycho_items(db)

        results = seed_canonical_psych_test_users(db, limit=4)
        db.commit()

        assert len(results) == 4
        assert all(result.psycho_score_version == "v2" for result in results)
        assert db.query(PsychoScore).count() == 4
        assert db.query(PsychoDerivedPattern).count() >= 4
        assert db.query(PsychoReport).count() == 4
        assert db.query(BehaviorFeature).count() == 4
        assert db.query(UserProfileState).count() == 4
        assert db.query(AuthUser).count() == 4
        assert db.query(User).filter(User.status == SYNTHETIC_TEST_USER_STATUS).count() == 4
        assert db.query(User).filter(User.email.like(f"%@{SYNTHETIC_TEST_EMAIL_DOMAIN}")).count() == 4

        report = build_psychology_migration_report(db)
        assert report.synthetic_users == 4
        assert report.synthetic_users_v2 == 4
        assert report.readiness.prelaunch_validation_ready is True
        assert report.readiness.readiness_status == "ready_for_prelaunch_validation"
        assert report.readiness.real_cutover_ready is False
    finally:
        db.close()
