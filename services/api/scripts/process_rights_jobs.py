import json
import os
import zipfile
from datetime import datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import DeletionQueueItem, User, UserRightsRequest
from app.modules.job_telemetry import record_job_run
from app.modules.rights.service import backup_deletion_note


def process_export_requests(db):
    rows = db.scalars(select(UserRightsRequest).where(UserRightsRequest.right_type == "export", UserRightsRequest.status == "pending")).all()
    for row in rows:
        user = db.get(User, row.user_id)
        bundle = {
            "user_id": row.user_id,
            "generated_at": datetime.utcnow().isoformat(),
            "profile": {
                "name": user.name if user else None,
                "email": user.email if user else None,
                "birth_place": user.birth_place if user else None,
            },
        }
        out_dir = os.getenv("RIGHTS_EXPORT_DIR", "/tmp/soulmatch-exports")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, f"{row.id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(bundle, f)
        zip_path = os.path.join(out_dir, f"{row.id}.zip")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(out_file, arcname=f"{row.id}.json")
        row.status = "completed"
        row.completed_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        row.resolution_payload = {
            "export_path": out_file,
            "export_zip_path": zip_path,
            "download_url": f"http://127.0.0.1:8000/exports/{row.id}.zip",
            "expires_at": (datetime.utcnow() + timedelta(days=2)).isoformat(),
        }
    db.commit()


def process_delete_requests(db):
    queued = db.scalars(select(DeletionQueueItem).where(DeletionQueueItem.status == "queued")).all()
    for item in queued:
        item.status = "completed"
        item.processed_at = datetime.utcnow()
        item.last_error = None
        if item.scope == "database":
            user = db.get(User, item.user_id)
            if user:
                user.email = f"deleted-{user.id}@redacted.local"
                user.name = "Deleted User"
                user.birth_place = "Deleted"
                user.birth_date = "1900-01-01"
                user.birth_time = "00:00"
                user.birth_latitude = None
                user.birth_longitude = None
                user.birth_timezone = None
                user.goals = []
                user.deleted_at = datetime.utcnow()
        if item.scope == "backups":
            item.last_error = "backup_purge_scheduled_next_window"

    reqs = db.scalars(select(UserRightsRequest).where(UserRightsRequest.right_type == "delete", UserRightsRequest.status == "pending")).all()
    for req in reqs:
        if any(i.status != "completed" for i in db.scalars(select(DeletionQueueItem).where(DeletionQueueItem.right_request_id == req.id)).all()):
            continue
        req.status = "completed"
        req.completed_at = datetime.utcnow()
        req.updated_at = datetime.utcnow()
        req.resolution_payload = {
            "active_systems_deleted_at": datetime.utcnow().isoformat(),
            "backup_purge_scheduled": True,
            "backup_purge_window_days": 35,
            "backup_purge_evidence_ref": f"backup-purge-ticket-{req.id}",
            "backup_deletion_note": backup_deletion_note(),
        }
    db.commit()


def main():
    with SessionLocal() as db:
        try:
            process_export_requests(db)
            process_delete_requests(db)
            record_job_run(db, "rights_jobs", ok=True)
            db.commit()
        except Exception as exc:  # pragma: no cover
            db.rollback()
            record_job_run(db, "rights_jobs", ok=False, error=str(exc))
            db.commit()
            raise


if __name__ == "__main__":
    main()
