from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status

from .database import get_db
from .models import AuthUser, LegalDocument, UserConsent
from .security import get_current_auth_user

REQUIRED_DOC_KEYS = ["PRIVACY_POLICY", "TERMS_OF_SERVICE", "AI_DISCLOSURE"]


def has_current_consent(db: Session, user_id: str) -> bool:
    for key in REQUIRED_DOC_KEYS:
        doc = db.scalar(select(LegalDocument).where(LegalDocument.key == key).order_by(LegalDocument.effective_at.desc()))
        if not doc:
            return False
        consent = db.scalar(
            select(UserConsent).where(
                UserConsent.user_id == user_id,
                UserConsent.doc_key == key,
                UserConsent.doc_version == doc.version,
            )
        )
        if not consent:
            return False
    return True


def require_current_consent(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
) -> None:
    if not has_current_consent(db, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="current_legal_consent_required")
