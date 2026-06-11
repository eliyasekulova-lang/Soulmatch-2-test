import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db
from .models import AuthUser
from .settings import get_settings

settings = get_settings()

JWT_SECRET = settings.jwt_secret
JWT_ALGORITHM = settings.jwt_algorithm
JWT_ACCESS_EXPIRE_MINUTES = settings.jwt_access_expire_minutes
JWT_REFRESH_EXPIRE_DAYS = settings.jwt_refresh_expire_days

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=True)
optional_bearer_scheme = HTTPBearer(auto_error=False)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(subject: str, role: str) -> tuple[str, datetime]:
    expire = utc_now() + timedelta(minutes=JWT_ACCESS_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": subject, "role": role, "type": "access", "exp": expire}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expire


def refresh_expiry() -> datetime:
    return utc_now() + timedelta(days=JWT_REFRESH_EXPIRE_DAYS)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def get_current_auth_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthUser:
    payload = decode_token(creds.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")

    user = db.get(AuthUser, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
    if user.role in {"suspended", "banned"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="account_restricted")
    return user


def get_optional_auth_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[AuthUser]:
    if not creds:
        return None
    payload = decode_token(creds.credentials)
    if not payload or payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return db.get(AuthUser, user_id)


def require_admin_user(current_user: AuthUser = Depends(get_current_auth_user)) -> AuthUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    if settings.app_env in {"staging", "production"} and settings.admin_emails:
        if current_user.email.lower() not in settings.admin_emails:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_email_not_allowed")
    return current_user
