from __future__ import annotations

from datetime import datetime, timedelta
import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.matching_preferences import preference_requires_astro
from app.models import BehaviorFeature, BehaviorSignalEvent, PsychoScore, User, UserProfileState
from app.services.eligibility import evaluate_eligibility
from app.services.psycho_scoring import clamp


def _safe_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def rollup_behavior_features(db: Session, user_id: str, window_days: int = 30) -> BehaviorFeature:
    since = datetime.utcnow() - timedelta(days=window_days)
    events = db.scalars(
        select(BehaviorSignalEvent)
        .where(BehaviorSignalEvent.user_id == user_id, BehaviorSignalEvent.created_at >= since)
        .order_by(BehaviorSignalEvent.created_at.asc())
    ).all()

    reply_ms: list[float] = []
    message_lengths: list[float] = []
    sentiment_values: list[float] = []
    active_days = set()
    initiations = 0
    reads = 0
    replies = 0
    boundary_violations = 0

    for event in events:
        payload = event.event_payload or {}
        active_days.add(event.created_at.date())

        if isinstance(payload.get("reply_ms"), (int, float)):
            reply_ms.append(float(payload["reply_ms"]))
        if isinstance(payload.get("message_length"), (int, float)):
            message_lengths.append(float(payload["message_length"]))
        if isinstance(payload.get("sentiment"), (int, float)):
            sentiment_values.append(float(payload["sentiment"]))
        if bool(payload.get("initiated")):
            initiations += 1
        if bool(payload.get("read")):
            reads += 1
        if bool(payload.get("replied")):
            replies += 1
        if bool(payload.get("boundary_violation")):
            boundary_violations += 1

    event_count = len(events)
    delay_std = _safe_std(reply_ms)
    delay_mean = (sum(reply_ms) / len(reply_ms)) if reply_ms else 0.0

    if reply_ms and delay_mean > 0:
        response_consistency = clamp(1.0 - (delay_std / delay_mean))
        response_delay_var = clamp(delay_std / 86_400_000.0)
    else:
        response_consistency = 0.5
        response_delay_var = 0.5

    initiative_ratio = clamp((initiations / event_count) if event_count else 0.5)

    if reads:
        reciprocity = replies / reads
    else:
        reciprocity = 0.5
    message_depth = clamp(((sum(message_lengths) / len(message_lengths)) / 280.0) if message_lengths else 0.5)
    conversation_balance = clamp((0.6 * reciprocity) + (0.4 * message_depth))

    engagement_stability = clamp((len(active_days) / max(1, window_days)) * 3.0)
    boundary_respect = clamp(1.0 - (boundary_violations / max(1, event_count)))

    if sentiment_values:
        sentiment_std = _safe_std(sentiment_values)
        emotional_variability = clamp(sentiment_std / 2.0)
    else:
        emotional_variability = 0.5

    vector = [
        round(response_consistency, 4),
        round(response_delay_var, 4),
        round(initiative_ratio, 4),
        round(conversation_balance, 4),
        round(engagement_stability, 4),
        round(boundary_respect, 4),
        round(emotional_variability, 4),
    ]

    completion = clamp(event_count / 40.0)
    confidence = clamp(0.1 + (0.9 * completion))
    uncertainty = [round(1.0 - confidence, 4)] * len(vector)

    feature = db.get(BehaviorFeature, user_id)
    if not feature:
        feature = BehaviorFeature(user_id=user_id)
        db.add(feature)

    feature.response_consistency = vector[0]
    feature.response_delay_var = vector[1]
    feature.initiative_ratio = vector[2]
    feature.conversation_balance = vector[3]
    feature.engagement_stability = vector[4]
    feature.boundary_respect = vector[5]
    feature.emotional_variability = vector[6]
    feature.behavior_vector = vector
    feature.behavior_uncertainty = uncertainty
    feature.computed_at = datetime.utcnow()

    state = db.get(UserProfileState, user_id)
    if not state:
        state = UserProfileState(user_id=user_id)
        db.add(state)

    state.behavior_completion = completion
    state.behavior_confidence = confidence

    psycho = db.get(PsychoScore, user_id)
    if psycho:
        profile = db.get(User, user_id)
        unc_avg = sum(psycho.psycho_uncertainty or [1.0]) / max(1, len(psycho.psycho_uncertainty or [1.0]))
        eligibility = evaluate_eligibility(
            astro_completion=1.0 if state.astro_complete else float(state.astro_completion or 0.0),
            psycho_completion=1.0 if state.psycho_complete else float(state.psycho_completion or 0.0),
            behavior_completion=completion,
            quality_flags=psycho.quality_flags or {},
            psycho_uncertainty_avg=unc_avg,
            require_astro=preference_requires_astro(profile.matching_preference if profile else None),
        )
        state.stage = eligibility.stage
        state.required_modules_complete = eligibility.required_modules_complete
        state.quality_pass = eligibility.quality_pass
        state.psycho_confidence = eligibility.psycho_confidence
        state.overall_confidence = eligibility.overall_confidence

    state.updated_at = datetime.utcnow()

    db.flush()
    return feature
