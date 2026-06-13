import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..legal_guard import require_current_consent
from ..matching_preferences import preference_requires_astro
from ..models import (
    AstroVector,
    AuthUser,
    BehaviorProfile,
    MatchResult,
    MatchV2,
    PsychProfile,
    User,
    UserProfileState,
)
from ..security import get_current_auth_user
from ..services.analytics import track as ph_track
from ..services.match_orchestration_service import compute_orchestrated_matches, replace_match_result_rows
from ..services.matching import explanation_reasons, explanation_watch_items
from ..settings import get_settings

router = APIRouter(tags=["matching"])
logger = logging.getLogger("soulmatch.api")


class MatchRequest(BaseModel):
    user_id: str
    mode: str = Field(pattern="^(romance|friendship)$")
    match_mode: str = Field(default="attraction", pattern="^(attraction|destiny)$")
    candidate_ids: list[str] | None = None


class MatchResultItem(BaseModel):
    candidate_id: str
    candidate_name: str
    candidate_city: str
    score: float
    highlights: list[str]
    mode: str | None = None


class MatchResponse(BaseModel):
    ok: bool
    mode: str | None = None
    match_mode: str | None = None
    results: list[MatchResultItem] = Field(default_factory=list)
    error: str | None = None
    message: str | None = None
    low_supply: bool = False


class MatchV2ResponseItem(BaseModel):
    other_user_id: str
    final_score: float
    confidence: float
    psycho_score: float
    astro_score: float
    behavior_score: float
    explanation: dict


class MatchExplainResponse(BaseModel):
    ok: bool
    user_id: str
    candidate_id: str
    match_mode: str
    mode: str
    reasons: list[str]
    watch_items: list[str]
    disclaimer: str


class MatchPredictionResponse(BaseModel):
    ok: bool
    user_id: str
    candidate_id: str
    match_mode: str
    mode: str
    intensity: float
    stability: float
    conflict_risk: float
    growth_potential: float
    disclaimer: str


class OpenersResponse(BaseModel):
    ok: bool
    user_id: str
    candidate_id: str
    tone: str
    suggestions: list[dict]
    disclaimer: str


class TimingResponse(BaseModel):
    ok: bool
    user_id: str
    candidate_id: str
    mode: str
    supportive_window: str
    challenging_window: str
    guidance: str
    disclaimer: str


class AdvisorRequest(BaseModel):
    user_id: str
    prompt: str = Field(min_length=4, max_length=1000)


class AdvisorResponse(BaseModel):
    ok: bool
    user_id: str
    response: str
    blocked: bool
    disclaimer: str


def _track_event_best_effort(db: Session, user_id: str | None, event_name: str, event_payload: dict | None = None) -> None:
    from ..models import AnalyticsEvent

    try:
        db.add(AnalyticsEvent(user_id=user_id, event_name=event_name, event_payload=event_payload or {}))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("analytics_event_write_failed")


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _safe_norm(v: float) -> float:
    return max(0.0, min(1.0, v))


def _astro_score(user_vector: list[float], candidate_vector: list[float], mode: str) -> float:
    base = (_cosine(user_vector, candidate_vector) + 1.0) / 2.0
    mode_shift = 0.05 if mode == "friendship" else 0.0
    return _safe_norm(base + mode_shift)


def _psych_score(user_psych: PsychProfile | None, candidate_psych: PsychProfile | None) -> float:
    if not user_psych or not candidate_psych:
        return 0.5
    a = user_psych.ocean_vector or []
    b = candidate_psych.ocean_vector or []
    if len(a) != 5 or len(b) != 5:
        return 0.5
    ocean_distance = sum(abs(x - y) for x, y in zip(a, b)) / 5.0
    ocean_sim = 1.0 - ocean_distance
    style_bonus = 0.08 if user_psych.communication_style == candidate_psych.communication_style else 0.0
    conflict_bonus = 0.06 if user_psych.conflict_style == candidate_psych.conflict_style else 0.0
    attachment_bonus = 0.05 if user_psych.attachment_style == candidate_psych.attachment_style else 0.0
    return _safe_norm(ocean_sim + style_bonus + conflict_bonus + attachment_bonus)


def _alignment_score(user: User | None, candidate: User | None) -> float:
    if not user or not candidate:
        return 0.5
    user_goals = set(user.goals or [])
    candidate_goals = set(candidate.goals or [])
    if not user_goals and not candidate_goals:
        return 0.5
    overlap = len(user_goals.intersection(candidate_goals))
    union = max(1, len(user_goals.union(candidate_goals)))
    return _safe_norm(overlap / union)


def _behavior_score(user_behavior: BehaviorProfile | None, candidate_behavior: BehaviorProfile | None) -> float:
    if not user_behavior or not candidate_behavior:
        return 0.5
    a = user_behavior.behavior_vector or []
    b = candidate_behavior.behavior_vector or []
    if len(a) != 6 or len(b) != 6:
        return 0.5
    distance = sum(abs(x - y) for x, y in zip(a, b)) / 6.0
    return _safe_norm(1.0 - distance)


def _compose_total(
    astro: float,
    psych: float,
    behavior: float,
    alignment: float,
    match_mode: str,
    include_astro: bool,
) -> float:
    # Attraction favors chemistry; Destiny favors stability/life alignment.
    if match_mode == "destiny":
        weights = {"astro": 0.25, "psych": 0.30, "behavior": 0.25, "alignment": 0.20}
    else:
        weights = {"astro": 0.40, "psych": 0.25, "behavior": 0.20, "alignment": 0.15}
    if not include_astro:
        weights["astro"] = 0.0
    active_total = sum(weights.values()) or 1.0
    total = (
        (astro * weights["astro"]) +
        (psych * weights["psych"]) +
        (behavior * weights["behavior"]) +
        (alignment * weights["alignment"])
    ) / active_total
    return _safe_norm(total)


def _prediction_from_match_v2(row: MatchV2) -> tuple[float, float, float, float]:
    dynamics = row.dynamics_payload or {}
    attachment = float(dynamics.get("attachment_compatibility") or 0.48)
    conflict = float(dynamics.get("conflict_compatibility") or 0.44)
    intimacy = float(dynamics.get("intimacy_pace_compatibility") or 0.48)
    stability_value = float(dynamics.get("stability_exploration_compatibility") or 0.5)
    compatibility_score = _safe_norm(float(getattr(row, "compatibility_score", 0.0) or row.final_score))
    intensity = _safe_norm((compatibility_score * 0.55) + (intimacy * 0.45))
    stability = _safe_norm((stability_value * 0.45) + (conflict * 0.30) + (attachment * 0.25))
    conflict_risk = _safe_norm(1.0 - ((conflict * 0.65) + (attachment * 0.35)))
    growth = _safe_norm((compatibility_score * 0.45) + (row.confidence * 0.25) + ((1.0 - conflict_risk) * 0.30))
    return intensity, stability, conflict_risk, growth


def _forward_only_blocked(prompt: str) -> bool:
    p = prompt.lower()
    blocked_patterns = [
        "why did my last relationship fail",
        "analyze my ex",
        "who ruined my relationship",
        "what was wrong with my ex",
        "why did it fail",
    ]
    return any(pattern in p for pattern in blocked_patterns)


def _require_eligible_profile(db: Session, user_id: str) -> None:
    state = db.get(UserProfileState, user_id)
    if not state or state.stage != "eligible":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="profile_incomplete")


def _low_supply_status(result_count: int) -> tuple[bool, str | None]:
    if result_count == 0:
        return True, "No strong matches are available right now. Check back soon as the pool grows."
    if result_count < 3:
        return True, "We found a smaller set right now. We'll refresh as more compatible profiles become available."
    return False, None


@router.get("/matches", response_model=list[MatchV2ResponseItem])
def get_matches_v2(
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    _require_eligible_profile(db, current_user.id)

    rows = (
        db.query(MatchV2)
        .filter(MatchV2.user_id == current_user.id)
        .order_by(MatchV2.final_score.desc())
        .limit(7)
        .all()
    )
    return [
        MatchV2ResponseItem(
            other_user_id=row.other_user_id,
            final_score=float(row.final_score),
            confidence=float(row.confidence),
            psycho_score=float(row.psycho_score),
            astro_score=float(row.astro_score),
            behavior_score=float(row.behavior_score),
            explanation=row.explanation or {},
        )
        for row in rows
    ]


@router.post("/matches", response_model=MatchResponse)
def match(
    payload: MatchRequest,
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if payload.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_user_mismatch")
    _require_eligible_profile(db, current_user.id)
    user_profile = db.get(User, payload.user_id)
    include_astro = preference_requires_astro(user_profile.matching_preference if user_profile else None)
    if include_astro and db.get(AstroVector, payload.user_id) is None:
        return {"ok": False, "error": "vector_missing"}

    rows = compute_orchestrated_matches(
        db,
        user_id=payload.user_id,
        mode=payload.mode,
        match_mode=payload.match_mode,
        candidate_ids=payload.candidate_ids,
    )
    results = [
        {
            "candidate_id": row.other_user_id,
            "candidate_name": row.candidate_name,
            "candidate_city": row.candidate_city,
            "score": round(row.rank_score * 100, 2),
            "highlights": row.highlights,
        }
        for row in rows
    ]
    replace_match_result_rows(db, user_id=payload.user_id, mode=payload.mode, rows=rows)
    db.commit()
    _track_event_best_effort(
        db,
        payload.user_id,
        "matches_generated",
        {"mode": payload.mode, "match_mode": payload.match_mode, "count": len(results)},
    )
    ph_track("matches_generated", distinct_id=payload.user_id, properties={"mode": payload.mode, "match_mode": payload.match_mode, "count": len(results), "low_supply": len(results) < 3}, api_key=get_settings().posthog_api_key)
    low_supply, message = _low_supply_status(len(results))
    return {
        "ok": True,
        "mode": payload.mode,
        "match_mode": payload.match_mode,
        "results": results,
        "message": message,
        "low_supply": low_supply,
    }


@router.get("/matches/{user_id}", response_model=MatchResponse)
def get_matches(
    user_id: str,
    mode: str | None = Query(default=None, pattern="^(romance|friendship)$"),
    match_mode: str = Query(default="attraction", pattern="^(attraction|destiny)$"),
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_user_mismatch")
    _require_eligible_profile(db, current_user.id)

    query = db.query(MatchResult).filter(MatchResult.user_id == user_id)
    if mode:
        query = query.filter(MatchResult.mode == mode)
    rows = query.order_by(MatchResult.score.desc()).all()

    candidate_ids = [r.candidate_id for r in rows]
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(candidate_ids))).all()}
    results = []
    for r in rows:
        u = users.get(r.candidate_id)
        results.append(
            {
                "candidate_id": r.candidate_id,
                "candidate_name": u.name if u else r.candidate_id,
                "candidate_city": (u.birth_place.split(",")[0].strip() if u else "Unknown"),
                "score": r.score,
                "highlights": r.highlights,
                "mode": r.mode,
            }
        )
    low_supply, message = _low_supply_status(len(results))
    return {
        "ok": True,
        "mode": mode,
        "match_mode": match_mode,
        "results": results,
        "message": message,
        "low_supply": low_supply,
    }


@router.get("/matches/{user_id}/explain/{candidate_id}", response_model=MatchExplainResponse)
def explain_match(
    user_id: str,
    candidate_id: str,
    mode: str = Query(default="romance", pattern="^(romance|friendship)$"),
    match_mode: str = Query(default="attraction", pattern="^(attraction|destiny)$"),
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_user_mismatch")
    _require_eligible_profile(db, current_user.id)

    base_row = db.query(MatchResult).filter(MatchResult.user_id == user_id, MatchResult.candidate_id == candidate_id).first()
    if not base_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="match_not_found")
    match_v2 = db.query(MatchV2).filter(MatchV2.user_id == user_id, MatchV2.other_user_id == candidate_id).first()
    if match_v2 is not None:
        reasons = explanation_reasons(match_v2.explanation or {}, limit=3)
        watch_items = explanation_watch_items(match_v2.explanation or {}, limit=2)
        confidence = float(match_v2.confidence or 0.0)
        if confidence < 0.5:
            reasons = reasons[:2]
            reasons.append("Current insight is still developing, so this explanation stays more tentative than usual.")
    else:
        reasons = [
            "Astrology compatibility indicates constructive momentum.",
            "Psychology profile overlap suggests communication ease.",
            "Values and goals show practical compatibility.",
        ]
        if match_mode == "destiny":
            reasons[0] = "Stability-oriented chart signals support long-term consistency."
        watch_items = [
            "Use direct check-ins to align expectations early.",
            "Treat compatibility as guidance and adapt through real communication.",
        ]
    return {
        "ok": True,
        "user_id": user_id,
        "candidate_id": candidate_id,
        "match_mode": match_mode,
        "mode": mode,
        "reasons": reasons,
        "watch_items": watch_items,
        "disclaimer": "Guidance only, not medical advice, and not deterministic.",
    }


@router.get("/matches/{user_id}/prediction/{candidate_id}", response_model=MatchPredictionResponse)
def match_prediction(
    user_id: str,
    candidate_id: str,
    mode: str = Query(default="romance", pattern="^(romance|friendship)$"),
    match_mode: str = Query(default="attraction", pattern="^(attraction|destiny)$"),
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_user_mismatch")
    _require_eligible_profile(db, current_user.id)

    base_row = db.query(MatchResult).filter(MatchResult.user_id == user_id, MatchResult.candidate_id == candidate_id).first()
    if not base_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="match_not_found")
    match_v2 = db.query(MatchV2).filter(MatchV2.user_id == user_id, MatchV2.other_user_id == candidate_id).first()
    if match_v2 is not None:
        intensity, stability, conflict_risk, growth = _prediction_from_match_v2(match_v2)
    else:
        score01 = _safe_norm(base_row.score / 100.0)
        stability = _safe_norm(score01 + (0.07 if match_mode == "destiny" else -0.02))
        intensity = _safe_norm(score01 + (0.08 if match_mode == "attraction" else -0.03))
        conflict_risk = _safe_norm(1.0 - ((stability + score01) / 2.0))
        growth = _safe_norm((stability + intensity) / 2.0)

    return {
        "ok": True,
        "user_id": user_id,
        "candidate_id": candidate_id,
        "match_mode": match_mode,
        "mode": mode,
        "intensity": round(intensity * 100, 2),
        "stability": round(stability * 100, 2),
        "conflict_risk": round(conflict_risk * 100, 2),
        "growth_potential": round(growth * 100, 2),
        "disclaimer": "Guidance only, not medical advice, and not deterministic.",
    }


@router.get("/matches/{user_id}/openers/{candidate_id}", response_model=OpenersResponse)
def match_openers(
    user_id: str,
    candidate_id: str,
    tone: str = Query(default="thoughtful", pattern="^(playful|direct|thoughtful|witty)$"),
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_user_mismatch")
    _require_eligible_profile(db, current_user.id)

    row = db.query(MatchResult).filter(MatchResult.user_id == user_id, MatchResult.candidate_id == candidate_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="match_not_found")

    by_tone = {
        "playful": "Quick question: are you more sunrise hike or midnight snack energy?",
        "direct": "I liked your profile and would love to get to know you. Want to chat this week?",
        "thoughtful": "Your communication style stood out to me. What helps you feel most understood early on?",
        "witty": "Serious compatibility check: what’s your top comfort meal after a long day?",
    }
    suggestions = [
        {"text": by_tone[tone], "rationale": "Matches your selected tone and keeps conversation low-pressure."},
        {"text": "What’s one small thing you’re excited about this week?", "rationale": "Encourages positive momentum."},
        {"text": "I value clear communication early. What does that look like for you?", "rationale": "Sets healthy expectations."},
        {"text": "Would you rather plan everything or be spontaneous on weekends?", "rationale": "Surfaces lifestyle rhythm."},
        {"text": "What kind of social energy recharges you most?", "rationale": "Checks alignment on social pace."},
    ]
    return {
        "ok": True,
        "user_id": user_id,
        "candidate_id": candidate_id,
        "tone": tone,
        "suggestions": suggestions,
        "disclaimer": "Suggestions only, not guarantees.",
    }


@router.get("/matches/{user_id}/timing/{candidate_id}", response_model=TimingResponse)
def match_timing(
    user_id: str,
    candidate_id: str,
    mode: str = Query(default="romance", pattern="^(romance|friendship)$"),
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_user_mismatch")
    _require_eligible_profile(db, current_user.id)
    row = db.query(MatchResult).filter(MatchResult.user_id == user_id, MatchResult.candidate_id == candidate_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="match_not_found")

    return {
        "ok": True,
        "user_id": user_id,
        "candidate_id": candidate_id,
        "mode": mode,
        "supportive_window": "next_7_to_21_days",
        "challenging_window": "next_22_to_30_days",
        "guidance": "Use the upcoming supportive window to build consistency and clear expectations.",
        "disclaimer": "Timing is guidance only, not deterministic.",
    }


@router.post("/advisor", response_model=AdvisorResponse)
def advisor(
    payload: AdvisorRequest,
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if payload.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_user_mismatch")

    if _forward_only_blocked(payload.prompt):
        return {
            "ok": True,
            "user_id": payload.user_id,
            "blocked": True,
            "response": "I can’t help with backward-looking failure analysis. I can help you with next-step communication, boundaries, or partner-priority strategy.",
            "disclaimer": "Guidance only, not medical advice, and not deterministic.",
        }

    response = (
        "Based on your prompt, prioritize clear boundaries early, ask one values-focused question, "
        "and keep pace aligned with mutual responsiveness."
    )
    _track_event_best_effort(db, payload.user_id, "advisor_prompt_processed", {"blocked": False})
    return {
        "ok": True,
        "user_id": payload.user_id,
        "blocked": False,
        "response": response,
        "disclaimer": "Guidance only, not medical advice, and not deterministic.",
    }
