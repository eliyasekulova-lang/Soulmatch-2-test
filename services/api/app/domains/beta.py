import asyncio
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import BetaSignup
from ..security import require_admin_user
from ..services.email import send_beta_welcome
from ..settings import get_settings

logger = logging.getLogger("soulmatch.beta")

router = APIRouter(prefix="/beta", tags=["beta"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class BetaSignupRequest(BaseModel):
    email: EmailStr
    city: str | None = None
    source: str = "landing_page"
    referral_code: str | None = None

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        allowed = {"landing_page", "referral", "social", "event", "direct"}
        return v if v in allowed else "landing_page"

    @field_validator("city")
    @classmethod
    def validate_city(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip()[:128] if v.strip() else None


class BetaSignupResponse(BaseModel):
    status: str
    message: str
    position: int | None = None


class BetaSignupRow(BaseModel):
    id: int
    email: str
    source: str
    city: str | None
    referral_code: str | None
    notified: bool
    created_at: str

    model_config = {"from_attributes": True}


def _send_beta_welcome_sync(to: str, position: int, api_key: str) -> None:
    asyncio.run(send_beta_welcome(to=to, position=position, resend_api_key=api_key))


@router.post("/signup", response_model=BetaSignupResponse, status_code=status.HTTP_201_CREATED)
def beta_signup(body: BetaSignupRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    existing = db.query(BetaSignup).filter(BetaSignup.email == body.email.lower()).first()
    if existing:
        position = db.query(BetaSignup).filter(BetaSignup.created_at <= existing.created_at).count()
        return BetaSignupResponse(
            status="already_registered",
            message="You're already on the list!",
            position=position,
        )

    signup = BetaSignup(
        email=body.email.lower(),
        source=body.source,
        city=body.city,
        referral_code=body.referral_code,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    try:
        db.add(signup)
        db.commit()
        db.refresh(signup)
    except IntegrityError:
        db.rollback()
        position = db.query(BetaSignup).count()
        return BetaSignupResponse(
            status="already_registered",
            message="You're already on the list!",
            position=position,
        )

    position = db.query(BetaSignup).filter(BetaSignup.created_at <= signup.created_at).count()
    logger.info("beta_signup", extra={"email_domain": body.email.split("@")[-1], "source": body.source})

    settings = get_settings()
    background_tasks.add_task(_send_beta_welcome_sync, body.email, position, settings.resend_api_key)

    return BetaSignupResponse(
        status="success",
        message="You're on the list! We'll reach out when your spot opens.",
        position=position,
    )


@router.get("/signups", response_model=list[BetaSignupRow])
def list_beta_signups(
    limit: int = 500,
    offset: int = 0,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin_user),
):
    rows = (
        db.query(BetaSignup)
        .order_by(BetaSignup.created_at.asc())
        .offset(offset)
        .limit(min(limit, 1000))
        .all()
    )
    return [
        BetaSignupRow(
            id=r.id,
            email=r.email,
            source=r.source,
            city=r.city,
            referral_code=r.referral_code,
            notified=r.notified,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.get("/count")
def beta_signup_count(db: Session = Depends(get_db)):
    count = db.query(BetaSignup).count()
    return {"count": count}
