from datetime import datetime

from sqlalchemy import select

from app.database import SessionLocal
from app.models import DeletionJob, MediaObject, User
from app.modules.job_telemetry import record_job_run
from app.modules.media.storage import LocalDevStorageAdapter


storage = LocalDevStorageAdapter()


def main():
    with SessionLocal() as db:
        try:
            jobs = db.scalars(select(DeletionJob).where(DeletionJob.status == "queued")).all()
            for job in jobs:
                try:
                    # Scrub profile data
                    user = db.get(User, job.user_id)
                    if user:
                        user.name = "Deleted User"
                        user.legal_name = "Deleted User"
                        user.email = f"deleted-{user.id}@redacted.local"
                        user.birth_place = "Deleted"
                        user.birth_city = None
                        user.birth_country = None
                        user.birth_date = "1900-01-01"
                        user.birth_time = "00:00"
                        user.birth_date_encrypted = None
                        user.birth_time_encrypted = None
                        user.birth_place_encrypted = None
                        user.goals = []
                        user.status = "deleted"
                        user.deleted_at = datetime.utcnow()

                    # Delete owned media objects from storage adapter
                    media_rows = db.scalars(select(MediaObject).where(MediaObject.owner_user_id == job.user_id)).all()
                    for media in media_rows:
                        storage.delete_object(media.storage_key)
                        media.status = "removed"

                    job.status = "completed"
                    job.updated_at = datetime.utcnow()
                    job.last_error = None
                except Exception as exc:  # pragma: no cover - defensive worker branch
                    job.status = "failed"
                    job.updated_at = datetime.utcnow()
                    job.last_error = str(exc)
            record_job_run(db, "deletion_jobs", ok=True)
            db.commit()
        except Exception as exc:  # pragma: no cover
            db.rollback()
            record_job_run(db, "deletion_jobs", ok=False, error=str(exc))
            db.commit()
            raise


if __name__ == "__main__":
    main()
