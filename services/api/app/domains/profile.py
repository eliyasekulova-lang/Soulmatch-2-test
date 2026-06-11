import logging
import re
from hashlib import sha256
from collections import defaultdict
from datetime import date, datetime, timedelta

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..database import get_db
from ..jobs.recompute_user import recompute_matches_for_user
from ..crypto import encrypt_pii
from ..legal_guard import require_current_consent
from ..matching_preferences import normalize_matching_preference
from ..models import (
    AnalyticsEvent,
    AuthUser,
    BehaviorFeature,
    BehaviorProfile,
    BehaviorSignalEvent,
    ConsentRecord,
    JobRunTelemetry,
    User,
    UserProfileState,
)
from ..models import ExperimentAssignment
from ..modules.behavior_service import compute_behavior_profile
from ..modules.safety_service import update_risk_for_event
from ..observability import get_error_metrics
from ..services.behavior_rollup import rollup_behavior_features
from ..services.weight_tuning import FEEDBACK_EVENT_NAMES
from ..runtime_state import startup_snapshot
from ..security import get_current_auth_user, get_optional_auth_user, require_admin_user
from ..settings import get_settings

router = APIRouter(tags=["profile"])
logger = logging.getLogger("soulmatch.api")
settings = get_settings()

CANONICAL_ANALYTICS_EVENTS = {
    "app_open",
    "onboarding_started",
    "onboarding_completed",
    "profile_upserted",
    "match_viewed",
    "match_liked",
    "match_passed",
    "message_sent",
    "message_replied",
    "subscription_checkout_started",
    "subscription_checkout_completed",
    "feedback_felt_understood",
    "feedback_effortless",
    "feedback_meet_again",
}

LOCAL_PLACE_FALLBACKS = [
    {"id": "fallback-toronto", "label": "Toronto, Ontario, Canada", "latitude": 43.6532, "longitude": -79.3832},
    {"id": "fallback-new-york", "label": "New York, NY, USA", "latitude": 40.7128, "longitude": -74.0060},
    {"id": "fallback-london", "label": "London, United Kingdom", "latitude": 51.5074, "longitude": -0.1278},
    {"id": "fallback-montreal", "label": "Montreal, Quebec, Canada", "latitude": 45.5017, "longitude": -73.5673},
    {"id": "fallback-vancouver", "label": "Vancouver, British Columbia, Canada", "latitude": 49.2827, "longitude": -123.1207},
]


class BirthData(BaseModel):
    date: str
    time: str
    place: str
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None

    @field_validator("date")
    @classmethod
    def validate_birth_date(cls, value: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            raise ValueError("date_must_be_yyyy_mm_dd")
        year, month, day = map(int, value.split("-"))
        try:
            date(year, month, day)
        except ValueError:
            raise ValueError("invalid_date")
        if year < 1900 or year > date.today().year:
            raise ValueError("date_out_of_supported_range")
        return value

    @field_validator("time")
    @classmethod
    def validate_birth_time(cls, value: str) -> str:
        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", value):
            raise ValueError("time_must_be_hh_mm_24h")
        return value


class UserCreate(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=255)
    email: str | None = None
    birth: BirthData
    goals: list[str] = Field(min_length=1)
    matching_preference: str = Field(default="psych_behavior_astro", pattern="^(psych_behavior|psych_behavior_astro)$")
    consent_privacy: bool
    consent_sensitive_data: bool
    policy_version: str = "v1"
    locale: str = Field(default="en-CA", max_length=16)
    jurisdiction: str = Field(default="CA", max_length=16)


class AnalyticsEventRequest(BaseModel):
    event_name: str
    event_payload: dict = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str


class HealthLiveResponse(BaseModel):
    status: str
    uptime_state: dict


class HealthReadyResponse(BaseModel):
    status: str
    checks: dict
    errors: dict


class JobsHealthResponse(BaseModel):
    ok: bool
    jobs: list[dict]
    error_counters: dict


class LegalSummaryResponse(BaseModel):
    summary: str
    policy_version: str | None = None
    terms_version: str | None = None


class PlaceSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=120)
    limit: int = Field(default=6, ge=1, le=10)


class PlaceResult(BaseModel):
    id: str | int
    label: str
    latitude: float
    longitude: float


class PlaceSearchResponse(BaseModel):
    ok: bool
    results: list[PlaceResult]


class UserUpsertResponse(BaseModel):
    ok: bool
    user_id: str


class MeResponse(BaseModel):
    ok: bool
    user_id: str
    name: str
    email: str | None
    locale: str
    jurisdiction: str
    matching_preference: str


class MePatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = None
    locale: str | None = Field(default=None, max_length=16)
    jurisdiction: str | None = Field(default=None, max_length=16)
    matching_preference: str | None = Field(default=None, pattern="^(psych_behavior|psych_behavior_astro)$")


class SeedCandidatesResponse(BaseModel):
    ok: bool
    inserted: int


class EventTrackResponse(BaseModel):
    ok: bool


class AnalyticsTaxonomyResponse(BaseModel):
    ok: bool
    schema_version: str
    events: list[str]


class AnalyticsFunnelStep(BaseModel):
    step: str
    users: int
    conversion_from_previous: float | None = None


class AnalyticsFunnelResponse(BaseModel):
    ok: bool
    user_scope: str
    window_days: int
    generated_at: str
    steps: list[AnalyticsFunnelStep]


class ExperimentAssignRequest(BaseModel):
    experiment_key: str = Field(min_length=3, max_length=64)
    variants: list[str] = Field(min_length=2, max_length=10)

    @field_validator("variants")
    @classmethod
    def validate_variants(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) < 2:
            raise ValueError("variants_min_two")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("variants_must_be_unique")
        return cleaned


class ExperimentAssignResponse(BaseModel):
    ok: bool
    experiment_key: str
    variant: str
    assigned_at: str
    exposure_logged: bool


class CohortPoint(BaseModel):
    cohort_date: str
    signups: int
    retained_d1: int
    retained_d7: int
    retained_d30: int


class AnalyticsRetentionResponse(BaseModel):
    ok: bool
    window_days: int
    generated_at: str
    cohorts: list[CohortPoint]


class AnalyticsKpiResponse(BaseModel):
    ok: bool
    window_days: int
    generated_at: str
    kpis: dict


class AnalyticsAnomaliesResponse(BaseModel):
    ok: bool
    generated_at: str
    anomalies: list[dict]


class BehaviorProfileResponse(BaseModel):
    ok: bool
    user_id: str
    window_days: int
    vector: list[float]
    dimensions: dict
    updated_at: str | None = None


class BehaviorAggregateRequest(BaseModel):
    user_id: str | None = None
    window_days: int = Field(default=30, ge=7, le=90)


class BehaviorAggregateResponse(BaseModel):
    ok: bool
    user_id: str
    window_days: int


def _track_event_best_effort(db: Session, user_id: str | None, event_name: str, event_payload: dict | None = None) -> None:
    try:
        db.add(AnalyticsEvent(user_id=user_id, event_name=event_name, event_payload=event_payload or {}))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("analytics_event_write_failed")


def _trigger_match_recompute_if_eligible(db: Session, user_id: str) -> int:
    state = db.get(UserProfileState, user_id)
    if not state or state.stage != "eligible":
        return 0
    return recompute_matches_for_user(db, user_id, top_k=20)


@router.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}


@router.get("/health/live", response_model=HealthLiveResponse)
def health_live():
    return {"status": "ok", "uptime_state": startup_snapshot()}


@router.get("/health/ready", response_model=HealthReadyResponse)
def health_ready(db: Session = Depends(get_db)):
    checks = {"database": False, "startup": False}
    errors = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as exc:
        errors["database"] = str(exc)
    snap = startup_snapshot()
    checks["startup"] = bool(snap.get("startup_ok"))
    if not checks["startup"]:
        errors["startup"] = snap.get("startup_error") or "startup_not_confirmed"

    status_value = "ok" if all(checks.values()) else "degraded"
    return {"status": status_value, "checks": checks, "errors": errors}


@router.get("/health/jobs", response_model=JobsHealthResponse)
def health_jobs(db: Session = Depends(get_db)):
    rows = db.query(JobRunTelemetry).order_by(JobRunTelemetry.job_name.asc()).all()
    jobs = [
        {
            "job_name": row.job_name,
            "status": row.status,
            "last_run_at": row.last_run_at.isoformat(),
            "run_count": row.run_count,
            "success_count": row.success_count,
            "failure_count": row.failure_count,
            "last_error": row.last_error,
        }
        for row in rows
    ]
    return {"ok": True, "jobs": jobs, "error_counters": get_error_metrics()}


@router.get("/legal/privacy", response_model=LegalSummaryResponse)
def legal_privacy():
    return {
        "policy_version": "v1",
        "summary": "Birth data is processed for compatibility matching and can be deleted on request.",
    }


@router.get("/legal/terms", response_model=LegalSummaryResponse)
def legal_terms():
    return {
        "terms_version": "v1",
        "summary": "Use of SoulMatch is subject to consent, privacy policy, and safe community rules.",
    }


@router.post("/places/search", response_model=PlaceSearchResponse)
def places_search(payload: PlaceSearchRequest):
    rows = []
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": payload.query.strip(), "format": "json", "addressdetails": 1, "limit": payload.limit},
            headers={"User-Agent": "SoulMatchAPI/0.5"},
            timeout=10,
        )
        response.raise_for_status()
        rows = response.json()
    except Exception:
        logger.warning("place_search_external_failed", extra={"query": payload.query})

    results = []
    for item in rows if isinstance(rows, list) else []:
        try:
            results.append(
                {
                    "id": item.get("place_id"),
                    "label": item.get("display_name", ""),
                    "latitude": float(item.get("lat")),
                    "longitude": float(item.get("lon")),
                }
            )
        except Exception:
            continue

    if not results:
        query = payload.query.strip().lower()
        fallback_matches = [
            item
            for item in LOCAL_PLACE_FALLBACKS
            if query in item["label"].lower() or any(token in item["label"].lower() for token in query.split())
        ]
        if not fallback_matches:
            fallback_matches = LOCAL_PLACE_FALLBACKS[:]
        results = fallback_matches[: payload.limit]

    return {"ok": True, "results": results}


@router.post("/users", response_model=UserUpsertResponse)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if payload.id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_user_mismatch")
    if not payload.consent_privacy or not payload.consent_sensitive_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="consent_required")

    try:
        dob = datetime.strptime(payload.birth.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_birth_date")
    age_years = (date.today() - dob).days // 365
    if age_years < settings.min_signup_age_years:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="age_restriction_under_minimum")

    matching_preference = normalize_matching_preference(payload.matching_preference)

    existing = db.get(User, payload.id)
    if existing:
        existing.name = payload.name
        existing.legal_name = payload.name
        existing.email = payload.email
        existing.birth_date = payload.birth.date
        existing.birth_time = payload.birth.time
        existing.birth_place = payload.birth.place
        place_parts = [p.strip() for p in payload.birth.place.split(",") if p.strip()]
        existing.birth_city = place_parts[0] if place_parts else payload.birth.place
        existing.birth_country = place_parts[-1] if len(place_parts) > 1 else "Unknown"
        existing.birth_latitude = payload.birth.latitude
        existing.birth_longitude = payload.birth.longitude
        existing.birth_timezone = payload.birth.timezone
        existing.birth_date_encrypted = encrypt_pii(payload.birth.date)
        existing.birth_time_encrypted = encrypt_pii(payload.birth.time)
        existing.birth_place_encrypted = encrypt_pii(payload.birth.place)
        existing.locale = payload.locale
        existing.jurisdiction = payload.jurisdiction
        existing.goals = payload.goals
        existing.matching_preference = matching_preference
        existing.status = "active"
    else:
        place_parts = [p.strip() for p in payload.birth.place.split(",") if p.strip()]
        db.add(
            User(
                id=payload.id,
                name=payload.name,
                legal_name=payload.name,
                email=payload.email,
                birth_date=payload.birth.date,
                birth_time=payload.birth.time,
                birth_place=payload.birth.place,
                birth_city=place_parts[0] if place_parts else payload.birth.place,
                birth_country=place_parts[-1] if len(place_parts) > 1 else "Unknown",
                birth_latitude=payload.birth.latitude,
                birth_longitude=payload.birth.longitude,
                birth_timezone=payload.birth.timezone,
                birth_date_encrypted=encrypt_pii(payload.birth.date),
                birth_time_encrypted=encrypt_pii(payload.birth.time),
                birth_place_encrypted=encrypt_pii(payload.birth.place),
                locale=payload.locale,
                jurisdiction=payload.jurisdiction,
                goals=payload.goals,
                matching_preference=matching_preference,
                status="active",
            )
        )
        db.flush()

    db.add(
        ConsentRecord(
            user_id=payload.id,
            privacy_accepted=payload.consent_privacy,
            sensitive_data_accepted=payload.consent_sensitive_data,
            policy_version=payload.policy_version or "v1",
        )
    )
    db.commit()
    try:
        _trigger_match_recompute_if_eligible(db, payload.id)
    except Exception:
        db.rollback()
        logger.exception("match_recompute_after_profile_upsert_failed")
    _track_event_best_effort(db, payload.id, "profile_upserted", {"goals": payload.goals})
    return {"ok": True, "user_id": payload.id}


@router.get("/me", response_model=MeResponse)
def me(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    profile = db.get(User, current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile_not_found")
    return {
        "ok": True,
        "user_id": profile.id,
        "name": profile.name,
        "email": profile.email,
        "locale": profile.locale,
        "jurisdiction": profile.jurisdiction,
        "matching_preference": normalize_matching_preference(profile.matching_preference),
    }


@router.patch("/me", response_model=MeResponse)
def patch_me(
    payload: MePatchRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    profile = db.get(User, current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile_not_found")
    if payload.name is not None:
        profile.name = payload.name.strip()
    if payload.email is not None:
        profile.email = payload.email.strip()
    if payload.locale is not None:
        profile.locale = payload.locale.strip()
    if payload.jurisdiction is not None:
        profile.jurisdiction = payload.jurisdiction.strip()
    if payload.matching_preference is not None:
        profile.matching_preference = normalize_matching_preference(payload.matching_preference)
    db.commit()
    try:
        _trigger_match_recompute_if_eligible(db, current_user.id)
    except Exception:
        db.rollback()
        logger.exception("match_recompute_after_profile_patch_failed")
    return {
        "ok": True,
        "user_id": profile.id,
        "name": profile.name,
        "email": profile.email,
        "locale": profile.locale,
        "jurisdiction": profile.jurisdiction,
        "matching_preference": normalize_matching_preference(profile.matching_preference),
    }


@router.post("/admin/seed-candidates", response_model=SeedCandidatesResponse)
def admin_seed_candidates(
    db: Session = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    from ..seed import seed_demo_candidates

    inserted = seed_demo_candidates(db)
    return {"ok": True, "inserted": inserted}


@router.post("/events", response_model=EventTrackResponse)
def track_event(
    payload: AnalyticsEventRequest,
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser | None = Depends(get_optional_auth_user),
):
    if payload.event_name not in CANONICAL_ANALYTICS_EVENTS and not payload.event_name.startswith("custom_"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown_event_name")
    normalized_payload = dict(payload.event_payload or {})
    normalized_payload.setdefault("schema_version", "v1")
    resolved_user_id = current_user.id if current_user else None
    if payload.event_name in FEEDBACK_EVENT_NAMES and not resolved_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="auth_required_for_feedback")

    if payload.event_name in {"feedback_felt_understood", "feedback_effortless"}:
        score = normalized_payload.get("score")
        if not isinstance(score, (int, float)) or float(score) < 1.0 or float(score) > 5.0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_feedback_score")
    if payload.event_name == "feedback_meet_again":
        if "yes" not in normalized_payload:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing_feedback_yes")
        if not isinstance(normalized_payload.get("yes"), bool):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_feedback_yes")

    db.add(AnalyticsEvent(user_id=resolved_user_id, event_name=payload.event_name, event_payload=normalized_payload))
    if resolved_user_id:
        db.add(
            BehaviorSignalEvent(
                user_id=resolved_user_id,
                event_type=payload.event_name,
                event_payload=normalized_payload,
            )
        )
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("analytics_event_write_failed")
        return {"ok": False}
    if resolved_user_id:
        try:
            update_risk_for_event(db, resolved_user_id, payload.event_name, normalized_payload)
            compute_behavior_profile(db, resolved_user_id, window_days=30)
            rollup_behavior_features(db, resolved_user_id, window_days=30)
            db.commit()
            _trigger_match_recompute_if_eligible(db, resolved_user_id)
        except Exception:
            db.rollback()
            logger.exception("post_event_processing_failed")
    return {"ok": True}


@router.get("/analytics/taxonomy", response_model=AnalyticsTaxonomyResponse)
def analytics_taxonomy():
    return {"ok": True, "schema_version": "v1", "events": sorted(CANONICAL_ANALYTICS_EVENTS) + ["custom_*"]}


@router.get("/analytics/funnel", response_model=AnalyticsFunnelResponse)
def analytics_funnel(
    window_days: int = 30,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if window_days < 1 or window_days > 90:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="window_days_out_of_range")
    since = datetime.utcnow() - timedelta(days=window_days)

    def _count_users(event_name: str) -> int:
        return (
            db.query(func.count(func.distinct(AnalyticsEvent.user_id)))
            .filter(
                AnalyticsEvent.user_id == current_user.id,
                AnalyticsEvent.event_name == event_name,
                AnalyticsEvent.created_at >= since,
            )
            .scalar()
            or 0
        )

    ordered_steps = [
        "onboarding_started",
        "onboarding_completed",
        "match_viewed",
        "message_sent",
        "subscription_checkout_completed",
    ]
    steps = []
    previous = None
    for step in ordered_steps:
        users = _count_users(step)
        conversion = None
        if previous and previous > 0:
            conversion = round((users / previous) * 100.0, 2)
        steps.append({"step": step, "users": users, "conversion_from_previous": conversion})
        previous = users

    return {
        "ok": True,
        "user_scope": current_user.id,
        "window_days": window_days,
        "generated_at": datetime.utcnow().isoformat(),
        "steps": steps,
    }


@router.post("/experiments/assign", response_model=ExperimentAssignResponse)
def assign_experiment(
    payload: ExperimentAssignRequest,
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    existing = db.scalar(
        select(ExperimentAssignment).where(
            ExperimentAssignment.user_id == current_user.id,
            ExperimentAssignment.experiment_key == payload.experiment_key,
        )
    )
    if existing:
        return {
            "ok": True,
            "experiment_key": existing.experiment_key,
            "variant": existing.variant_key,
            "assigned_at": existing.assigned_at.isoformat(),
            "exposure_logged": False,
        }

    assignment_hash = sha256(f"{current_user.id}:{payload.experiment_key}".encode("utf-8")).hexdigest()
    variant_index = int(assignment_hash[:8], 16) % len(payload.variants)
    variant = payload.variants[variant_index]
    now = datetime.utcnow()
    db.add(
        ExperimentAssignment(
            user_id=current_user.id,
            experiment_key=payload.experiment_key,
            variant_key=variant,
            assignment_hash=assignment_hash,
            assigned_at=now,
            created_at=now,
        )
    )
    db.add(
        AnalyticsEvent(
            user_id=current_user.id,
            event_name="experiment_exposure",
            event_payload={
                "schema_version": "v1",
                "experiment_key": payload.experiment_key,
                "variant": variant,
            },
            created_at=now,
        )
    )
    db.commit()
    return {
        "ok": True,
        "experiment_key": payload.experiment_key,
        "variant": variant,
        "assigned_at": now.isoformat(),
        "exposure_logged": True,
    }


@router.get("/admin/analytics/retention", response_model=AnalyticsRetentionResponse)
def admin_analytics_retention(
    window_days: int = 30,
    db: Session = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    if window_days < 1 or window_days > 180:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="window_days_out_of_range")

    since = datetime.utcnow() - timedelta(days=window_days)
    users = db.scalars(select(AuthUser).where(AuthUser.created_at >= since)).all()
    cohorts: dict[str, list[AuthUser]] = defaultdict(list)
    for user in users:
        cohorts[user.created_at.date().isoformat()].append(user)

    points = []
    for cohort_date in sorted(cohorts.keys()):
        cohort_users = cohorts[cohort_date]
        retained_d1 = 0
        retained_d7 = 0
        retained_d30 = 0
        for user in cohort_users:
            d1_cutoff = user.created_at + timedelta(days=1)
            d7_cutoff = user.created_at + timedelta(days=7)
            d30_cutoff = user.created_at + timedelta(days=30)
            d1 = db.scalar(
                select(func.count(AnalyticsEvent.id)).where(
                    AnalyticsEvent.user_id == user.id,
                    AnalyticsEvent.created_at >= d1_cutoff,
                )
            )
            d7 = db.scalar(
                select(func.count(AnalyticsEvent.id)).where(
                    AnalyticsEvent.user_id == user.id,
                    AnalyticsEvent.created_at >= d7_cutoff,
                )
            )
            d30 = db.scalar(
                select(func.count(AnalyticsEvent.id)).where(
                    AnalyticsEvent.user_id == user.id,
                    AnalyticsEvent.created_at >= d30_cutoff,
                )
            )
            retained_d1 += 1 if (d1 or 0) > 0 else 0
            retained_d7 += 1 if (d7 or 0) > 0 else 0
            retained_d30 += 1 if (d30 or 0) > 0 else 0

        points.append(
            {
                "cohort_date": cohort_date,
                "signups": len(cohort_users),
                "retained_d1": retained_d1,
                "retained_d7": retained_d7,
                "retained_d30": retained_d30,
            }
        )

    return {"ok": True, "window_days": window_days, "generated_at": datetime.utcnow().isoformat(), "cohorts": points}


@router.get("/admin/analytics/kpis", response_model=AnalyticsKpiResponse)
def admin_analytics_kpis(
    window_days: int = 30,
    db: Session = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    if window_days < 1 or window_days > 180:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="window_days_out_of_range")
    since = datetime.utcnow() - timedelta(days=window_days)

    signups = db.scalar(select(func.count(AuthUser.id)).where(AuthUser.created_at >= since)) or 0
    onboarding_completed = (
        db.scalar(
            select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.event_name == "onboarding_completed",
                AnalyticsEvent.created_at >= since,
            )
        )
        or 0
    )
    match_viewed = (
        db.scalar(
            select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.event_name == "match_viewed",
                AnalyticsEvent.created_at >= since,
            )
        )
        or 0
    )
    message_sent = (
        db.scalar(
            select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.event_name == "message_sent",
                AnalyticsEvent.created_at >= since,
            )
        )
        or 0
    )
    checkout_completed = (
        db.scalar(
            select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.event_name == "subscription_checkout_completed",
                AnalyticsEvent.created_at >= since,
            )
        )
        or 0
    )

    def pct(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round((numerator / denominator) * 100.0, 2)

    return {
        "ok": True,
        "window_days": window_days,
        "generated_at": datetime.utcnow().isoformat(),
        "kpis": {
            "signups": signups,
            "onboarding_completed_users": onboarding_completed,
            "match_viewed_users": match_viewed,
            "message_sent_users": message_sent,
            "checkout_completed_users": checkout_completed,
            "onboarding_completion_rate": pct(onboarding_completed, signups),
            "match_to_message_rate": pct(message_sent, match_viewed),
            "message_to_checkout_rate": pct(checkout_completed, message_sent),
        },
    }


@router.get("/admin/analytics/anomalies", response_model=AnalyticsAnomaliesResponse)
def admin_analytics_anomalies(
    window_days: int = 7,
    db: Session = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    if window_days < 1 or window_days > 30:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="window_days_out_of_range")
    since = datetime.utcnow() - timedelta(days=window_days)
    viewed = (
        db.scalar(
            select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.event_name == "match_viewed",
                AnalyticsEvent.created_at >= since,
            )
        )
        or 0
    )
    messaged = (
        db.scalar(
            select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.event_name == "message_sent",
                AnalyticsEvent.created_at >= since,
            )
        )
        or 0
    )
    anomalies = []
    if viewed >= 10:
        conversion = (messaged / viewed) * 100.0
        if conversion < 5.0:
            anomalies.append(
                {
                    "type": "low_match_to_message_conversion",
                    "severity": "warning",
                    "observed_value": round(conversion, 2),
                    "threshold": 5.0,
                    "window_days": window_days,
                }
            )
    return {"ok": True, "generated_at": datetime.utcnow().isoformat(), "anomalies": anomalies}


@router.get("/profile/behavior", response_model=BehaviorProfileResponse)
def get_behavior_profile(
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    profile = db.get(BehaviorProfile, current_user.id)
    if not profile:
        profile = compute_behavior_profile(db, current_user.id, window_days=30)
    rollup_behavior_features(db, current_user.id, window_days=30)
    db.commit()
    db.refresh(profile)
    return {
        "ok": True,
        "user_id": current_user.id,
        "window_days": profile.window_days,
        "vector": profile.behavior_vector,
        "dimensions": {
            "reply_time_score": profile.reply_time_score,
            "conversation_depth_score": profile.conversation_depth_score,
            "consistency_score": profile.consistency_score,
            "receptiveness_score": profile.receptiveness_score,
            "boundary_respect_score": profile.boundary_respect_score,
            "initiation_balance_score": profile.initiation_balance_score,
        },
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


@router.post("/admin/behavior/aggregate", response_model=BehaviorAggregateResponse)
def admin_behavior_aggregate(
    payload: BehaviorAggregateRequest,
    db: Session = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    target_user_id = payload.user_id
    if not target_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id_required")
    profile = compute_behavior_profile(db, target_user_id, window_days=payload.window_days)
    rollup_behavior_features(db, target_user_id, window_days=payload.window_days)
    db.commit()
    _trigger_match_recompute_if_eligible(db, target_user_id)
    return {"ok": True, "user_id": profile.user_id, "window_days": payload.window_days}
