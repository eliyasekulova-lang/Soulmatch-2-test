from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalyticsEvent


FEEDBACK_EVENT_UNDERSTOOD = "feedback_felt_understood"
FEEDBACK_EVENT_EFFORTLESS = "feedback_effortless"
FEEDBACK_EVENT_MEET_AGAIN = "feedback_meet_again"
FEEDBACK_EVENT_NAMES = {
    FEEDBACK_EVENT_UNDERSTOOD,
    FEEDBACK_EVENT_EFFORTLESS,
    FEEDBACK_EVENT_MEET_AGAIN,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _norm_1_5(value: float) -> float:
    return _clamp((value - 1.0) / 4.0, 0.0, 1.0)


def derive_feedback_weight_multipliers(db: Session, user_id: str, window_days: int = 90) -> tuple[float, float, float, int]:
    since = datetime.utcnow() - timedelta(days=window_days)
    rows = db.scalars(
        select(AnalyticsEvent).where(
            AnalyticsEvent.user_id == user_id,
            AnalyticsEvent.event_name.in_(tuple(FEEDBACK_EVENT_NAMES)),
            AnalyticsEvent.created_at >= since,
        )
    ).all()

    understood_scores: list[float] = []
    effortless_scores: list[float] = []
    meet_again_values: list[float] = []

    for row in rows:
        payload = row.event_payload or {}
        if row.event_name == FEEDBACK_EVENT_UNDERSTOOD and isinstance(payload.get("score"), (int, float)):
            understood_scores.append(float(payload["score"]))
        elif row.event_name == FEEDBACK_EVENT_EFFORTLESS and isinstance(payload.get("score"), (int, float)):
            effortless_scores.append(float(payload["score"]))
        elif row.event_name == FEEDBACK_EVENT_MEET_AGAIN:
            if isinstance(payload.get("yes"), bool):
                meet_again_values.append(1.0 if payload["yes"] else 0.0)
            elif isinstance(payload.get("score"), (int, float)):
                meet_again_values.append(1.0 if float(payload["score"]) >= 1.0 else 0.0)

    understood_norm = (
        _norm_1_5(sum(understood_scores) / len(understood_scores)) if understood_scores else 0.5
    )
    effortless_norm = (
        _norm_1_5(sum(effortless_scores) / len(effortless_scores)) if effortless_scores else 0.5
    )
    meet_again_ratio = (sum(meet_again_values) / len(meet_again_values)) if meet_again_values else 0.5

    psycho_multiplier = _clamp(0.9 + (0.25 * understood_norm), 0.8, 1.2)
    astro_multiplier = _clamp(0.85 + (0.25 * meet_again_ratio), 0.8, 1.2)
    behavior_multiplier = _clamp(0.8 + (0.35 * meet_again_ratio) + (0.15 * effortless_norm), 0.75, 1.3)

    feedback_count = len(understood_scores) + len(effortless_scores) + len(meet_again_values)
    return psycho_multiplier, astro_multiplier, behavior_multiplier, feedback_count
