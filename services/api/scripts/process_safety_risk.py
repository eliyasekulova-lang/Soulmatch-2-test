from datetime import datetime, timedelta

from sqlalchemy import distinct, select

from app.database import SessionLocal
from app.models import Message
from app.modules.job_telemetry import record_job_run
from app.modules.safety_service import recompute_risk_from_recent_activity


def main() -> None:
    since = datetime.utcnow() - timedelta(days=7)
    with SessionLocal() as db:
        try:
            user_ids = db.scalars(select(distinct(Message.sender_user_id)).where(Message.created_at >= since)).all()
            processed = 0
            for user_id in user_ids:
                recompute_risk_from_recent_activity(db, user_id)
                processed += 1
            record_job_run(db, "safety_risk", ok=True)
            db.commit()
        except Exception as exc:  # pragma: no cover
            db.rollback()
            record_job_run(db, "safety_risk", ok=False, error=str(exc))
            db.commit()
            raise
    print({"ok": True, "processed_users": processed})


if __name__ == "__main__":
    main()
