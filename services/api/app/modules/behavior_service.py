from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BehaviorProfile, BehaviorSignalEvent


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_behavior_profile(db: Session, user_id: str, window_days: int = 30) -> BehaviorProfile:
    since = datetime.utcnow() - timedelta(days=window_days)
    events = db.scalars(
        select(BehaviorSignalEvent)
        .where(BehaviorSignalEvent.user_id == user_id, BehaviorSignalEvent.created_at >= since)
        .order_by(BehaviorSignalEvent.created_at.asc())
    ).all()

    if not events:
        vector = [0.5] * 6
        profile = db.get(BehaviorProfile, user_id)
        if profile:
            profile.reply_time_score = vector[0]
            profile.conversation_depth_score = vector[1]
            profile.consistency_score = vector[2]
            profile.receptiveness_score = vector[3]
            profile.boundary_respect_score = vector[4]
            profile.initiation_balance_score = vector[5]
            profile.behavior_vector = vector
            profile.window_days = window_days
            profile.updated_at = datetime.utcnow()
            db.flush()
            return profile
        profile = BehaviorProfile(
            user_id=user_id,
            reply_time_score=vector[0],
            conversation_depth_score=vector[1],
            consistency_score=vector[2],
            receptiveness_score=vector[3],
            boundary_respect_score=vector[4],
            initiation_balance_score=vector[5],
            behavior_vector=vector,
            window_days=window_days,
        )
        db.add(profile)
        db.flush()
        return profile

    reply_ms_values: list[float] = []
    msg_lengths: list[float] = []
    questions = 0
    reads = 0
    replies = 0
    boundary_violations = 0
    initiations = 0
    total_interactions = 0
    active_days = set()

    for event in events:
        payload = event.event_payload or {}
        active_days.add(event.created_at.date())

        if "reply_ms" in payload and isinstance(payload["reply_ms"], (int, float)):
            reply_ms_values.append(float(payload["reply_ms"]))
        if "message_length" in payload and isinstance(payload["message_length"], (int, float)):
            msg_lengths.append(float(payload["message_length"]))
            total_interactions += 1
        if bool(payload.get("asked_question")):
            questions += 1
        if bool(payload.get("read")):
            reads += 1
        if bool(payload.get("replied")):
            replies += 1
        if bool(payload.get("boundary_violation")):
            boundary_violations += 1
        if bool(payload.get("initiated")):
            initiations += 1

    avg_reply_ms = (sum(reply_ms_values) / len(reply_ms_values)) if reply_ms_values else 8_640_000.0
    reply_time_score = _clamp01(1.0 - (avg_reply_ms / 86_400_000.0))

    avg_msg_len = (sum(msg_lengths) / len(msg_lengths)) if msg_lengths else 80.0
    question_ratio = (questions / total_interactions) if total_interactions else 0.2
    conversation_depth_score = _clamp01((avg_msg_len / 280.0) * 0.7 + question_ratio * 0.3)

    consistency_score = _clamp01((len(active_days) / max(1, window_days)) * 3.0)
    receptiveness_score = _clamp01((replies / max(1, reads)) if reads else 0.5)
    boundary_respect_score = _clamp01(1.0 - (boundary_violations / max(1, len(events))))

    initiation_ratio = initiations / max(1, len(events))
    initiation_balance_score = _clamp01(1.0 - abs(initiation_ratio - 0.5) * 2.0)

    vector = [
        round(reply_time_score, 4),
        round(conversation_depth_score, 4),
        round(consistency_score, 4),
        round(receptiveness_score, 4),
        round(boundary_respect_score, 4),
        round(initiation_balance_score, 4),
    ]

    profile = db.get(BehaviorProfile, user_id)
    if profile:
        profile.reply_time_score = vector[0]
        profile.conversation_depth_score = vector[1]
        profile.consistency_score = vector[2]
        profile.receptiveness_score = vector[3]
        profile.boundary_respect_score = vector[4]
        profile.initiation_balance_score = vector[5]
        profile.behavior_vector = vector
        profile.window_days = window_days
        profile.updated_at = datetime.utcnow()
        db.flush()
        return profile

    profile = BehaviorProfile(
        user_id=user_id,
        reply_time_score=vector[0],
        conversation_depth_score=vector[1],
        consistency_score=vector[2],
        receptiveness_score=vector[3],
        boundary_respect_score=vector[4],
        initiation_balance_score=vector[5],
        behavior_vector=vector,
        window_days=window_days,
    )
    db.add(profile)
    db.flush()
    return profile
