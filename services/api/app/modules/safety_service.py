from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..models import Message, SafetyActionLog, TrustSafetyRisk

RISK_BANDS = [
    (75, "critical"),
    (50, "high"),
    (25, "medium"),
    (0, "low"),
]


def _band_for(score: float) -> str:
    for threshold, band in RISK_BANDS:
        if score >= threshold:
            return band
    return "low"


def _contains_any(text: str, terms: list[str]) -> bool:
    t = text.lower()
    return any(term in t for term in terms)


def _score_from_message_body(body: str) -> tuple[float, list[str], bool]:
    score = 0.0
    reasons: list[str] = []
    lower = body.lower()

    if _contains_any(lower, ["send money", "wire", "crypto", "loan", "urgent help"]):
        score += 28
        reasons.append("FRAUD_CUE")
    if _contains_any(lower, ["only trust me", "do not tell", "don't tell your friends", "don't tell family"]):
        score += 24
        reasons.append("ISOLATION_CUE")
    if _contains_any(lower, ["soulmate", "destiny", "meant for each other", "love of my life"]):
        score += 12
        reasons.append("LOVE_BOMBING_CUE")
    if _contains_any(lower, ["if you cared", "you owe me", "prove it"]):
        score += 12
        reasons.append("COERCIVE_LANGUAGE")

    hide_for_recipient = _contains_any(lower, ["wire", "send money", "loan", "urgent help", "only trust me"]) 
    return score, reasons, hide_for_recipient


def update_risk_for_event(db: Session, user_id: str, event_name: str, payload: dict | None = None) -> TrustSafetyRisk:
    payload = payload or {}
    risk = db.get(TrustSafetyRisk, user_id)
    if not risk:
        risk = TrustSafetyRisk(user_id=user_id, risk_score=0.0, risk_band="low", reason_codes=[])
        db.add(risk)
        db.flush()

    added_score = 0.0
    reason_codes: set[str] = set(risk.reason_codes or [])

    if event_name == "message_sent":
        body = str(payload.get("body", ""))
        body_score, reasons, _ = _score_from_message_body(body)
        added_score += body_score
        reason_codes.update(reasons)

    if payload.get("boundary_violation"):
        added_score += 20
        reason_codes.add("BOUNDARY_VIOLATION")

    if payload.get("report_filed"):
        added_score += 18
        reason_codes.add("REPORT_RATE_SPIKE")

    # Time-decay and additive update.
    base = max(0.0, risk.risk_score * 0.92)
    new_score = min(100.0, base + added_score)
    new_band = _band_for(new_score)

    if new_band != risk.risk_band:
        db.add(
            SafetyActionLog(
                user_id=user_id,
                action_type=f"risk_band_{new_band}",
                meta={"previous": risk.risk_band, "next": new_band, "score": round(new_score, 2)},
            )
        )

    risk.risk_score = round(new_score, 2)
    risk.risk_band = new_band
    risk.reason_codes = sorted(reason_codes)
    risk.last_evaluated_at = datetime.utcnow()
    risk.updated_at = datetime.utcnow()
    db.flush()
    return risk


def enforce_message_friction(db: Session, sender_user_id: str) -> tuple[bool, str | None]:
    risk = db.get(TrustSafetyRisk, sender_user_id)
    band = risk.risk_band if risk else "low"

    now = datetime.utcnow()
    one_day_ago = now - timedelta(days=1)
    sent_last_day = db.query(Message).filter(Message.sender_user_id == sender_user_id, Message.created_at >= one_day_ago).count()

    if band == "critical":
        db.add(SafetyActionLog(user_id=sender_user_id, action_type="message_blocked_critical", meta={"count_24h": sent_last_day}))
        db.flush()
        return False, "We’re limiting some actions to keep the community safe."

    if band == "high" and sent_last_day >= 20:
        db.add(SafetyActionLog(user_id=sender_user_id, action_type="message_throttled_high", meta={"count_24h": sent_last_day}))
        db.flush()
        return False, "We’re limiting some actions to keep the community safe."

    if band == "medium" and sent_last_day >= 40:
        db.add(SafetyActionLog(user_id=sender_user_id, action_type="message_throttled_medium", meta={"count_24h": sent_last_day}))
        db.flush()
        return False, "We’re limiting some actions to keep the community safe."

    return True, None


def recipient_protection_flags(db: Session, counterparty_user_id: str | None) -> dict:
    flags = {
        "show_boundary_prompts": True,
        "show_suspicious_pattern_warning": False,
        "auto_hide_enabled": True,
    }
    if not counterparty_user_id:
        return flags

    risk = db.get(TrustSafetyRisk, counterparty_user_id)
    if not risk:
        return flags

    if risk.risk_band in {"high", "critical"}:
        flags["show_suspicious_pattern_warning"] = True
    return flags


def should_hide_message_for_recipient(body: str, sender_user_id: str, db: Session) -> bool:
    _score, _reasons, hide = _score_from_message_body(body)
    risk = db.get(TrustSafetyRisk, sender_user_id)
    if risk and risk.risk_band == "critical":
        return True
    return hide


def recompute_risk_from_recent_activity(db: Session, user_id: str) -> TrustSafetyRisk:
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    msgs = db.scalars(select(Message).where(and_(Message.sender_user_id == user_id, Message.created_at >= week_ago))).all()

    score = 0.0
    reasons: set[str] = set()
    if len(msgs) > 120:
        score += 35
        reasons.add("MESSAGING_VELOCITY")
    elif len(msgs) > 60:
        score += 18
        reasons.add("MESSAGING_VELOCITY")

    for msg in msgs[-80:]:
        s, r, _hide = _score_from_message_body(msg.body)
        score += min(8, s / 4)
        reasons.update(r)

    score = min(100.0, score)
    band = _band_for(score)

    risk = db.get(TrustSafetyRisk, user_id)
    if not risk:
        risk = TrustSafetyRisk(user_id=user_id)
        db.add(risk)

    risk.risk_score = round(score, 2)
    risk.risk_band = band
    risk.reason_codes = sorted(reasons)
    risk.last_evaluated_at = datetime.utcnow()
    risk.updated_at = datetime.utcnow()
    db.flush()
    return risk
