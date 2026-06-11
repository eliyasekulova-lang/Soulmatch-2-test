import hashlib
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..legal_guard import REQUIRED_DOC_KEYS
from ..models import (
    AuthUser,
    DeletionJob,
    LegalDocument,
    PrivacyRequest,
    RefreshToken,
    User,
    UserConsent,
)
from ..security import get_current_auth_user, hash_refresh_token, utc_now

router = APIRouter(tags=["legal"])

LEGAL_DIR = Path(__file__).resolve().parents[4] / "legal"
DOC_MAP = {
    "PRIVACY_POLICY": "privacy-policy.md",
    "TERMS_OF_SERVICE": "terms-of-service.md",
    "ACCEPTABLE_USE_POLICY": "acceptable-use-policy.md",
    "AI_DISCLOSURE": "ai-disclosure.md",
    "TRUST_AND_SAFETY": "trust-and-safety.md",
    "DATA_RETENTION": "data-retention.md",
    "CONSENT_NOTICE": "consent-notice.md",
}


class LegalConsentRequest(BaseModel):
    accept: bool = Field(default=True)


class PrivacyRequestCreate(BaseModel):
    type: str = Field(pattern="^(EXPORT|DELETE|ACCESS|CORRECT)$")
    notes: str | None = Field(default=None, max_length=4000)


def _doc_content(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def seed_legal_documents(db: Session) -> None:
    now = datetime.utcnow()
    for key, filename in DOC_MAP.items():
        content = _doc_content(LEGAL_DIR / filename)
        if not content:
            continue
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        current = db.scalar(select(LegalDocument).where(LegalDocument.key == key).order_by(desc(LegalDocument.effective_at)))
        if current and current.checksum == checksum:
            continue
        next_version = "v1" if not current else f"v{int(current.version[1:]) + 1 if current.version.startswith('v') and current.version[1:].isdigit() else 1}"
        db.add(
            LegalDocument(
                key=key,
                version=next_version,
                effective_at=now,
                checksum=checksum,
                created_at=now,
            )
        )
    db.commit()


@router.get("/legal/docs")
def legal_docs(
    db: Session = Depends(get_db),
    _current_user: AuthUser = Depends(get_current_auth_user),
):
    out = []
    for key, filename in DOC_MAP.items():
        doc = db.scalar(select(LegalDocument).where(LegalDocument.key == key).order_by(desc(LegalDocument.effective_at)))
        if not doc:
            continue
        out.append(
            {
                "key": key,
                "version": doc.version,
                "effective_at": doc.effective_at.isoformat(),
                "filename": filename,
            }
        )
    return {"ok": True, "docs": out}


@router.get("/legal/docs/{key}")
def legal_doc_by_key(
    key: str,
    db: Session = Depends(get_db),
    _current_user: AuthUser = Depends(get_current_auth_user),
):
    if key not in DOC_MAP:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="legal_doc_not_found")
    doc = db.scalar(select(LegalDocument).where(LegalDocument.key == key).order_by(desc(LegalDocument.effective_at)))
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="legal_doc_not_found")
    content = _doc_content(LEGAL_DIR / DOC_MAP[key])
    return {
        "ok": True,
        "key": key,
        "version": doc.version,
        "effective_at": doc.effective_at.isoformat(),
        "content": content,
    }


@router.post("/legal/consent")
def legal_consent(
    payload: LegalConsentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if not payload.accept:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="consent_not_granted")

    now = datetime.utcnow()
    stored = []
    for key in REQUIRED_DOC_KEYS:
        doc = db.scalar(select(LegalDocument).where(LegalDocument.key == key).order_by(desc(LegalDocument.effective_at)))
        if not doc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"required_doc_missing:{key}")

        exists = db.scalar(
            select(UserConsent).where(
                UserConsent.user_id == current_user.id,
                UserConsent.doc_key == key,
                UserConsent.doc_version == doc.version,
            )
        )
        if exists:
            stored.append({"doc_key": key, "doc_version": doc.version, "consented_at": exists.consented_at.isoformat()})
            continue

        consent = UserConsent(
            user_id=current_user.id,
            doc_key=key,
            doc_version=doc.version,
            consented_at=now,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(consent)
        db.flush()
        stored.append({"doc_key": key, "doc_version": doc.version, "consented_at": consent.consented_at.isoformat()})

    db.commit()
    return {"ok": True, "consents": stored}


@router.get("/legal/consent/status")
def legal_consent_status(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    out = []
    for key in REQUIRED_DOC_KEYS:
        doc = db.scalar(select(LegalDocument).where(LegalDocument.key == key).order_by(desc(LegalDocument.effective_at)))
        if not doc:
            out.append({"doc_key": key, "required_version": None, "consented": False})
            continue
        consent = db.scalar(
            select(UserConsent).where(
                UserConsent.user_id == current_user.id,
                UserConsent.doc_key == key,
                UserConsent.doc_version == doc.version,
            )
        )
        out.append(
            {
                "doc_key": key,
                "required_version": doc.version,
                "consented": bool(consent),
                "consented_at": consent.consented_at.isoformat() if consent else None,
            }
        )
    return {"ok": True, "status": out}


@router.post("/legal/privacy-requests")
def create_privacy_request(
    payload: PrivacyRequestCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    now = datetime.utcnow()
    req = PrivacyRequest(
        id=f"pr-{uuid.uuid4().hex[:16]}",
        user_id=current_user.id,
        type=payload.type,
        status="OPEN",
        created_at=now,
        updated_at=now,
        notes=payload.notes,
    )
    db.add(req)
    db.commit()
    return {"ok": True, "request_id": req.id, "status": req.status}


@router.get("/legal/privacy-requests")
def list_privacy_requests(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    rows = db.scalars(select(PrivacyRequest).where(PrivacyRequest.user_id == current_user.id).order_by(desc(PrivacyRequest.created_at))).all()
    return {
        "ok": True,
        "requests": [
            {
                "id": row.id,
                "type": row.type,
                "status": row.status,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
                "notes": row.notes,
            }
            for row in rows
        ],
    }


@router.get("/legal/export-data")
def export_data(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    user = db.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile_not_found")

    # High-level aggregate only for behavior profile.
    from ..models import AnalyticsEvent
    from ..models import BehaviorProfile
    from ..models import Message
    from ..models import PsychProfile

    event_count = db.query(AnalyticsEvent).filter(AnalyticsEvent.user_id == current_user.id).count()
    last_event = db.scalar(
        select(AnalyticsEvent).where(AnalyticsEvent.user_id == current_user.id).order_by(desc(AnalyticsEvent.created_at))
    )
    message_count = db.query(Message).filter(Message.sender_user_id == current_user.id).count()

    psych = db.get(PsychProfile, current_user.id)
    behavior = db.get(BehaviorProfile, current_user.id)

    # No raw safety risk score or internal reason codes included.
    return {
        "ok": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
        },
        "birth_data": {
            "date": user.birth_date,
            "time": user.birth_time,
            "place": user.birth_place,
            "timezone": user.birth_timezone,
        },
        "psych_profile": (
            {
                "ocean_vector": psych.ocean_vector,
                "attachment_style": psych.attachment_style,
                "love_language": psych.love_language,
                "communication_style": psych.communication_style,
                "conflict_style": psych.conflict_style,
                "social_energy": psych.social_energy,
            }
            if psych
            else {"status": "not_available"}
        ),
        "behavior_profile": {
            "event_count": event_count,
            "last_event_at": last_event.created_at.isoformat() if last_event else None,
            "vector": behavior.behavior_vector if behavior else None,
            "window_days": behavior.window_days if behavior else None,
        },
        "messages_summary": {
            "sent_count": message_count,
            "content_exported": False,
        },
    }


@router.delete("/legal/delete-account")
def delete_account(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    now = utc_now().replace(tzinfo=None)

    req = PrivacyRequest(
        id=f"pr-{uuid.uuid4().hex[:16]}",
        user_id=current_user.id,
        type="DELETE",
        status="OPEN",
        created_at=now,
        updated_at=now,
        notes="delete_account_endpoint",
    )
    db.add(req)

    job = DeletionJob(
        id=f"djob-{uuid.uuid4().hex[:16]}",
        user_id=current_user.id,
        rights_request_id=None,
        status="queued",
        scope={"targets": ["database", "file_storage", "backups", "search_indexes", "analytics"]},
        created_at=now,
        updated_at=now,
        last_error=None,
    )
    db.add(job)

    user = db.get(User, current_user.id)
    if user:
        user.status = "DELETION_REQUESTED"
        user.deleted_at = now

    # Revoke refresh tokens immediately.
    tokens = db.scalars(select(RefreshToken).where(RefreshToken.user_id == current_user.id)).all()
    for token in tokens:
        token.revoked_at = now
        token.token_hash = hash_refresh_token(f"revoked-{token.id}-{now.isoformat()}")

    # Restrict auth user immediately.
    current_user.role = "suspended"

    db.commit()
    return {"ok": True, "privacy_request_id": req.id, "deletion_job_id": job.id, "status": "queued"}
