from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from ..models import JobRunTelemetry


def record_job_run(db: Session, job_name: str, ok: bool, error: str | None = None) -> None:
    row = db.get(JobRunTelemetry, job_name)
    now = datetime.utcnow()
    if not row:
        row = JobRunTelemetry(
            job_name=job_name,
            status="ok" if ok else "failed",
            last_run_at=now,
            run_count=1,
            success_count=1 if ok else 0,
            failure_count=0 if ok else 1,
            last_error=(None if ok else (error or "unknown_error")[:2000]),
            updated_at=now,
        )
        db.add(row)
        db.flush()
        return

    row.run_count += 1
    if ok:
        row.success_count += 1
        row.status = "ok"
        row.last_error = None
    else:
        row.failure_count += 1
        row.status = "failed"
        row.last_error = (error or "unknown_error")[:2000]
    row.last_run_at = now
    row.updated_at = now
    db.flush()
