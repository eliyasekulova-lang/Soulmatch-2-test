from datetime import datetime, timedelta

from sqlalchemy import distinct, select

from app.database import SessionLocal
from app.models import BehaviorSignalEvent
from app.modules.behavior_service import compute_behavior_profile
from app.modules.job_telemetry import record_job_run


def main() -> None:
    window_days = 30
    since = datetime.utcnow() - timedelta(days=window_days)
    processed = 0

    with SessionLocal() as db:
        try:
            user_ids = db.scalars(
                select(distinct(BehaviorSignalEvent.user_id)).where(BehaviorSignalEvent.created_at >= since)
            ).all()

            for user_id in user_ids:
                compute_behavior_profile(db, user_id, window_days=window_days)
                processed += 1
            record_job_run(db, "behavior_profiles", ok=True)
            db.commit()
        except Exception as exc:  # pragma: no cover - defensive worker branch
            db.rollback()
            record_job_run(db, "behavior_profiles", ok=False, error=str(exc))
            db.commit()
            raise

    print({"ok": True, "processed_users": processed, "window_days": window_days})


if __name__ == "__main__":
    main()
