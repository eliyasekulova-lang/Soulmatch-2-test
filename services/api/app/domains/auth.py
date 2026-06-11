import logging
import re
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuthUser, RefreshToken
from ..security import (
    create_access_token,
    generate_refresh_token,
    get_current_auth_user,
    hash_password,
    hash_refresh_token,
    refresh_expiry,
    utc_now,
    verify_password,
)
from ..rate_limit import limit_auth_identity_requests, limit_auth_requests, limit_refresh_requests
from ..settings import get_settings

router = APIRouter(tags=["auth"])
settings = get_settings()
logger = logging.getLogger("soulmatch.api")


class AuthSignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=1024)
    birth_date: str = Field(min_length=10, max_length=10, description="YYYY-MM-DD")


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=1024)


class AuthRefreshRequest(BaseModel):
    refresh_token: str


class AuthTokenResponse(BaseModel):
    ok: bool
    access_token: str
    access_token_expires_at: str
    refresh_token: str
    refresh_token_expires_at: str
    token_type: str
    user_id: str
    role: str


class AuthMeResponse(BaseModel):
    ok: bool
    user_id: str
    email: EmailStr
    role: str


class AuthLogoutResponse(BaseModel):
    ok: bool


def _validate_signup_age(birth_date_value: str) -> None:
    try:
        year, month, day = [int(x) for x in birth_date_value.split("-")]
        dob = date(year, month, day)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_birth_date")
    age_years = (date.today() - dob).days // 365
    if age_years < settings.min_signup_age_years:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="age_restriction_under_minimum")


def _validate_password_strength(password: str) -> None:
    # Release-grade baseline: at least one uppercase, lowercase, number, symbol.
    if len(password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password_too_short")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password_requires_uppercase")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password_requires_lowercase")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password_requires_number")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="password_requires_symbol")


def _track_event_best_effort(db: Session, user_id: str | None, event_name: str, event_payload: dict | None = None) -> None:
    from ..models import AnalyticsEvent

    try:
        db.add(AnalyticsEvent(user_id=user_id, event_name=event_name, event_payload=event_payload or {}))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("analytics_event_write_failed")


def _issue_tokens(db: Session, auth_user: AuthUser) -> dict:
    access_token, access_expires_at = create_access_token(auth_user.id, auth_user.role)
    refresh_token = generate_refresh_token()
    refresh_token_id = f"rt-{uuid.uuid4().hex}"
    refresh_expires_at = refresh_expiry()

    db.add(
        RefreshToken(
            id=refresh_token_id,
            user_id=auth_user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_expires_at,
            revoked_at=None,
        )
    )
    db.commit()
    return {
        "access_token": access_token,
        "access_token_expires_at": access_expires_at.isoformat(),
        "refresh_token": refresh_token,
        "refresh_token_expires_at": refresh_expires_at.isoformat(),
        "token_type": "bearer",
        "user_id": auth_user.id,
        "role": auth_user.role,
    }


def _revoke_refresh_token(db: Session, raw_refresh_token: str) -> RefreshToken | None:
    token_hash = hash_refresh_token(raw_refresh_token)
    token_row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if not token_row:
        return None
    token_row.revoked_at = utc_now().replace(tzinfo=None)
    db.commit()
    return token_row


@router.post("/auth/signup", response_model=AuthTokenResponse)
def auth_signup(
    payload: AuthSignupRequest,
    request: Request,
    _rl: None = Depends(limit_auth_requests),
    db: Session = Depends(get_db),
):
    limit_auth_identity_requests(request.client.host if request.client else "unknown", payload.email)
    _validate_signup_age(payload.birth_date)
    _validate_password_strength(payload.password)
    existing = db.scalar(select(AuthUser).where(AuthUser.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email_exists")

    role = "admin" if payload.email.lower() in settings.admin_emails else "user"
    user_id = f"usr-{uuid.uuid4().hex[:16]}"
    auth_user = AuthUser(id=user_id, email=payload.email, password_hash=hash_password(payload.password), role=role)
    db.add(auth_user)
    db.commit()
    _track_event_best_effort(db, user_id, "auth_signup", {"email": payload.email, "role": role})
    return {"ok": True, **_issue_tokens(db, auth_user)}


@router.post("/auth/login", response_model=AuthTokenResponse)
def auth_login(
    payload: AuthLoginRequest,
    request: Request,
    _rl: None = Depends(limit_auth_requests),
    db: Session = Depends(get_db),
):
    limit_auth_identity_requests(request.client.host if request.client else "unknown", payload.email)
    auth_user = db.scalar(select(AuthUser).where(AuthUser.email == payload.email))
    if not auth_user or not verify_password(payload.password, auth_user.password_hash):
        _track_event_best_effort(db, None, "auth_login_failed", {"email": payload.email})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    _track_event_best_effort(db, auth_user.id, "auth_login", {})
    return {"ok": True, **_issue_tokens(db, auth_user)}


@router.post("/auth/refresh", response_model=AuthTokenResponse)
def auth_refresh(
    payload: AuthRefreshRequest,
    request: Request,
    _rl: None = Depends(limit_auth_requests),
    db: Session = Depends(get_db),
):
    limit_refresh_requests(request)
    token_hash = hash_refresh_token(payload.refresh_token)
    refresh_row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if not refresh_row:
        _track_event_best_effort(db, None, "auth_refresh_failed", {"reason": "invalid_refresh_token"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh_token")
    if refresh_row.revoked_at is not None:
        _track_event_best_effort(db, refresh_row.user_id, "auth_refresh_failed", {"reason": "refresh_token_revoked"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh_token_revoked")
    if refresh_row.expires_at < utc_now().replace(tzinfo=None):
        _track_event_best_effort(db, refresh_row.user_id, "auth_refresh_failed", {"reason": "refresh_token_expired"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh_token_expired")

    auth_user = db.get(AuthUser, refresh_row.user_id)
    if not auth_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
    refresh_row.revoked_at = utc_now().replace(tzinfo=None)
    db.commit()
    _track_event_best_effort(db, auth_user.id, "auth_refresh", {})
    return {"ok": True, **_issue_tokens(db, auth_user)}


@router.post("/auth/logout", response_model=AuthLogoutResponse)
def auth_logout(payload: AuthRefreshRequest, db: Session = Depends(get_db)):
    token_row = _revoke_refresh_token(db, payload.refresh_token)
    if not token_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh_token")
    _track_event_best_effort(db, token_row.user_id, "auth_logout", {})
    return {"ok": True}


@router.get("/auth/me", response_model=AuthMeResponse)
def auth_me(current_user: AuthUser = Depends(get_current_auth_user)):
    return {"ok": True, "user_id": current_user.id, "email": current_user.email, "role": current_user.role}
