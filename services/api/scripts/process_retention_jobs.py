from datetime import datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditLog, Message, RetentionRule
from app.modules.job_telemetry import record_job_run


def main():
    with SessionLocal() as db:
        try:
            rules = {r.data_class: r for r in db.scalars(select(RetentionRule)).all()}
            msg_rule = rules.get("messages")
            if msg_rule:
                cutoff = datetime.utcnow() - timedelta(days=msg_rule.ttl_days)
                rows = db.scalars(select(Message).where(Message.created_at < cutoff)).all()
                for row in rows:
                    if msg_rule.purge_mode == "hard_delete":
                        db.delete(row)
                    else:
                        row.body = "[retained-message-redacted]"
            audit_rule = rules.get("audit_logs")
            if audit_rule:
                cutoff = datetime.utcnow() - timedelta(days=audit_rule.ttl_days)
                db.query(AuditLog).filter(AuditLog.created_at < cutoff).delete()
            record_job_run(db, "retention_jobs", ok=True)
            db.commit()
        except Exception as exc:  # pragma: no cover
            db.rollback()
            record_job_run(db, "retention_jobs", ok=False, error=str(exc))
            db.commit()
            raise


if __name__ == "__main__":
    main()
