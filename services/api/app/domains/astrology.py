import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..astro import BirthInput, chart_to_vector, compute_chart
from ..database import get_db
from ..models import AstroVector, AuthUser, User
from ..security import get_current_auth_user

router = APIRouter(tags=["astrology"])
logger = logging.getLogger("soulmatch.api")


class VectorGenerateRequest(BaseModel):
    user_id: str


class VectorGenerateResponse(BaseModel):
    ok: bool
    dims: int | None = None
    error: str | None = None


class NatalRequest(BaseModel):
    user_id: str


class NatalResponse(BaseModel):
    ok: bool
    user_id: str
    chart: dict


class SynastryRequest(BaseModel):
    user_id: str
    target_user_id: str
    mode: str = Field(default="romance", pattern="^(romance|friendship)$")


class SynastryResponse(BaseModel):
    ok: bool
    user_id: str
    target_user_id: str
    mode: str
    score: float
    summary: list[str]


def _track_event_best_effort(db: Session, user_id: str | None, event_name: str, event_payload: dict | None = None) -> None:
    from ..models import AnalyticsEvent

    try:
        db.add(AnalyticsEvent(user_id=user_id, event_name=event_name, event_payload=event_payload or {}))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("analytics_event_write_failed")


def _generate_vector_for_user(user: User, dims: int = 256) -> list[float]:
    chart = compute_chart(
        BirthInput(
            date=user.birth_date,
            time=user.birth_time,
            place=user.birth_place,
            latitude=user.birth_latitude,
            longitude=user.birth_longitude,
            timezone=user.birth_timezone,
        )
    )
    return chart_to_vector(chart, dims=dims)


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@router.post("/vectors/generate", response_model=VectorGenerateResponse)
def generate_vector(
    payload: VectorGenerateRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if payload.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_user_mismatch")

    user = db.get(User, payload.user_id)
    if not user:
        return {"ok": False, "error": "user_not_found"}

    vec = _generate_vector_for_user(user)
    existing = db.get(AstroVector, payload.user_id)
    if existing:
        existing.vector = vec
        existing.schema_version = "v1"
    else:
        db.add(AstroVector(user_id=payload.user_id, vector=vec, schema_version="v1"))
    db.commit()
    _track_event_best_effort(db, payload.user_id, "vector_generated", {"dims": len(vec)})
    return {"ok": True, "dims": len(vec)}


@router.post("/astrology/natal", response_model=NatalResponse)
def natal(
    payload: NatalRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if payload.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_user_mismatch")

    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile_not_found")

    chart = compute_chart(
        BirthInput(
            date=user.birth_date,
            time=user.birth_time,
            place=user.birth_place,
            latitude=user.birth_latitude,
            longitude=user.birth_longitude,
            timezone=user.birth_timezone,
        )
    )
    _track_event_best_effort(db, payload.user_id, "natal_chart_computed", None)
    return {"ok": True, "user_id": payload.user_id, "chart": chart}


@router.post("/astrology/synastry", response_model=SynastryResponse)
def synastry(
    payload: SynastryRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if payload.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_user_mismatch")
    if payload.user_id == payload.target_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_must_differ")

    user = db.get(User, payload.user_id)
    target = db.get(User, payload.target_user_id)
    if not user or not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile_not_found")

    user_vec = _generate_vector_for_user(user)
    target_vec = _generate_vector_for_user(target)
    base = (_cosine(user_vec, target_vec) + 1.0) / 2.0
    mode_bias = 0.03 if payload.mode == "friendship" else 0.0
    score = round(max(0.0, min(1.0, base + mode_bias)) * 100, 2)

    summary = [
        "Strong emotional rhythm overlap",
        "Communication style appears complementary",
        "Use direct check-ins to keep expectations aligned",
    ]
    _track_event_best_effort(
        db,
        payload.user_id,
        "synastry_computed",
        {"target_user_id": payload.target_user_id, "mode": payload.mode, "score": score},
    )
    return {
        "ok": True,
        "user_id": payload.user_id,
        "target_user_id": payload.target_user_id,
        "mode": payload.mode,
        "score": score,
        "summary": summary,
    }
