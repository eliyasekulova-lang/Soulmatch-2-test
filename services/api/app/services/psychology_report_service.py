from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models import PsychoReport

if TYPE_CHECKING:
    from .assessment_flow_service import PsychAssessmentSummary


def create_versioned_psychology_report(
    db: Session,
    *,
    user_id: str,
    summary: PsychAssessmentSummary,
) -> PsychoReport:
    report = PsychoReport(
        user_id=user_id,
        session_id=summary.session.id,
        report_version=_next_report_version(db, user_id=user_id),
        personality_summary=_personality_summary(summary.scored.traits),
        relationship_style=_relationship_style(summary.scored.traits, summary),
        conflict_style=_conflict_style(summary.scored.traits, summary),
        attachment_style=_attachment_style(summary.scored.traits, summary),
        affection_needs=_affection_needs(summary.scored.traits),
        blind_spots=_blind_spots(list(summary.contradiction_summary.meaningful_tensions)),
        best_match_type=_best_match_type(summary.scored.traits),
        growth_suggestions=_growth_suggestions(list(summary.contradiction_summary.meaningful_tensions)),
        confidence_summary=_confidence_summary(summary),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(report)
    db.flush()
    return report


def get_latest_psychology_report(db: Session, *, user_id: str) -> PsychoReport | None:
    reports = list_psychology_reports(db, user_id=user_id, limit=1)
    return reports[0] if reports else None


def list_psychology_reports(
    db: Session,
    *,
    user_id: str,
    limit: int | None = None,
) -> list[PsychoReport]:
    query = (
        db.query(PsychoReport)
        .filter(PsychoReport.user_id == user_id)
        .order_by(PsychoReport.created_at.desc(), PsychoReport.id.desc())
    )
    if limit is not None:
        query = query.limit(int(limit))
    return list(query.all())


def get_psychology_report_history(db: Session, *, user_id: str) -> list[PsychoReport]:
    return list_psychology_reports(db, user_id=user_id)


def _next_report_version(db: Session, *, user_id: str) -> str:
    latest = get_latest_psychology_report(db, user_id=user_id)
    if latest is None:
        return "r1"
    try:
        last_number = int(str(latest.report_version).lstrip("r"))
    except ValueError:
        last_number = latest.id or 0
    return f"r{last_number + 1}"


def _personality_summary(traits: dict[str, float]) -> str:
    openness = "curious and growth-oriented" if traits.get("O", 0.5) >= 0.6 else "steady and familiarity-oriented"
    conscientiousness = "reliable in follow-through" if traits.get("C", 0.5) >= 0.6 else "more flexible than structured"
    social = "socially energized" if traits.get("E", 0.5) >= 0.6 else "selective with social energy"
    return f"You may come across as {openness}, {conscientiousness}, and {social} in many everyday situations."


def _relationship_style(traits: dict[str, float], summary: PsychAssessmentSummary) -> str:
    pattern_map = {pattern.pattern_key: pattern for pattern in summary.derived_patterns}
    intimacy = pattern_map.get("intimacy_pace")
    if intimacy and getattr(intimacy, "pattern_score", 0.5) >= 0.6:
        return "You may warm into closeness relatively quickly once trust feels established."
    if traits.get("independence_need", 0.5) >= 0.65:
        return "You may value closeness alongside a clear sense of space and self-direction."
    return "You may prefer a balanced rhythm of connection, trust-building, and personal space."


def _conflict_style(traits: dict[str, float], summary: PsychAssessmentSummary) -> str:
    pattern_map = {pattern.pattern_key: pattern for pattern in summary.derived_patterns}
    repair = pattern_map.get("conflict_repair_style")
    if repair and getattr(repair, "pattern_score", 0.5) >= 0.65:
        return "In some situations, you may do best when tension is addressed clearly and with enough steadiness to repair it well."
    if traits.get("conflict_delay", 0.5) >= 0.6:
        return "You may prefer a little time to think before returning to difficult conversations."
    if traits.get("conflict_avoid", 0.5) >= 0.6:
        return "You may sometimes protect harmony by holding concerns back longer than you mean to."
    return "You may lean toward a measured, fairly direct approach to working through disagreement."


def _attachment_style(traits: dict[str, float], summary: PsychAssessmentSummary) -> str:
    pattern_map = {pattern.pattern_key: pattern for pattern in summary.derived_patterns}
    security = pattern_map.get("relational_security_profile")
    if security and getattr(security, "pattern_score", 0.5) >= 0.65:
        return "You may often feel grounded in closeness while still staying open and trusting."
    if traits.get("att_anxiety", 0.5) >= 0.65:
        return "At times, uncertainty in connection may feel more noticeable for you and lead to a desire for reassurance."
    if traits.get("att_avoid", 0.5) >= 0.65:
        return "You may protect your independence carefully when closeness starts to feel intense."
    return "Your attachment tendencies may be fairly balanced, with some variation depending on trust and context."


def _affection_needs(traits: dict[str, float]) -> str:
    options = [
        ("focused attention and quality time", traits.get("aff_attention", 0.5)),
        ("physical closeness", traits.get("aff_touch", 0.5)),
        ("spoken appreciation", traits.get("aff_words", 0.5)),
        ("practical gestures", traits.get("aff_acts", 0.5)),
        ("thoughtful gifts", traits.get("aff_gifts", 0.5)),
    ]
    top_two = ", ".join(label for label, _ in sorted(options, key=lambda item: item[1], reverse=True)[:2])
    return f"You may feel most cared for through {top_two}."


def _blind_spots(tensions: list[str]) -> str:
    if "closeness_and_independence_pull" in tensions:
        return "You may sometimes want strong connection and strong autonomy at the same time, which can make pacing important."
    if "exploration_with_stability_pull" in tensions:
        return "You may sometimes want novelty and predictability together, which can create mixed signals around change."
    if "harmony_with_low_directness" in tensions:
        return "You may occasionally protect harmony so much that your own needs become less visible."
    return "One possible blind spot is assuming others can infer your pace or needs without enough direct conversation."


def _best_match_type(traits: dict[str, float]) -> str:
    if traits.get("value_stability", 0.5) >= 0.65:
        return "You may pair well with someone who brings consistency, warmth, and clear follow-through."
    if traits.get("value_novelty", 0.5) >= 0.65:
        return "You may pair well with someone who is open to growth, variety, and shared experimentation."
    return "You may pair well with someone who combines steadiness with openness to each other’s pace."


def _growth_suggestions(tensions: list[str]) -> str:
    if tensions:
        return "A useful next step may be naming your pace, reassurance needs, and conflict preferences earlier so expectations stay clear."
    return "A useful next step may be noticing which situations bring out your most grounded communication and recreating more of that context."


def _confidence_summary(summary: PsychAssessmentSummary) -> str:
    answered = int(summary.scored.scoring_metadata.get("answered_item_count", 0))
    reflection = float(summary.scored.quality_flags.get("reflection_score", 0.0))
    followup_count = len(summary.answered_followup_item_ids)
    if answered >= 20 and reflection >= 0.4 and followup_count > 0:
        return "This summary may be directionally useful, with added confidence from the clarification prompts completed in this session."
    if answered >= 20 and reflection >= 0.4:
        return "This summary may be directionally useful, though it still reflects a snapshot rather than a fixed truth."
    return "This summary may offer a helpful starting point, with confidence likely to improve as more consistent assessment data is gathered."
