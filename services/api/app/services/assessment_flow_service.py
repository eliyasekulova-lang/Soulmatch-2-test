from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.matching_preferences import preference_requires_astro
from app.models import (
    BehaviorFeature,
    PsychoAssessmentSession,
    PsychoDerivedPattern,
    PsychoItem,
    PsychoItemResponse,
    PsychoResponse,
    PsychoScore,
    PsychoReport,
    User,
    UserProfileState,
)
from app.psychology_item_bank import get_standard_item_bank, is_followup_item

from .adaptive_assessment_service import MAX_FOLLOWUPS_PER_SESSION, AdaptiveDecision, decide_adaptive_followup
from .contradiction_mapping_service import ContradictionMappingResult
from .derived_patterns_service import DerivedPattern, derive_patterns
from .eligibility import evaluate_eligibility
from .psychology_event_service import emit_psychology_completion_events
from .psychology_report_service import create_versioned_psychology_report, get_latest_psychology_report
from .psychology_response_adapter import NormalizedPsychologyResponse, adapt_assessment_item_responses
from .psychology_scoring_service import (
    PsychologyScoreResult,
    build_legacy_psycho_score_payload,
    score_psychology_responses,
)
from .response_timing_service import ResponseTimingSummary


STANDARD_ASSESSMENT_MODE = "standard"
ONBOARDING_ASSESSMENT_MODE = "onboarding_v2"


@dataclass(frozen=True)
class PsychAssessmentSummary:
    session: PsychoAssessmentSession
    normalized_responses: dict[str, NormalizedPsychologyResponse]
    scored: PsychologyScoreResult
    legacy_traits: dict[str, float]
    legacy_vector: list[float]
    legacy_uncertainty: list[float]
    derived_patterns: list[DerivedPattern]
    timing_summary: ResponseTimingSummary
    contradiction_summary: ContradictionMappingResult
    answered_followup_item_ids: set[str]


@dataclass(frozen=True)
class AssessmentWriteResult:
    session: PsychoAssessmentSession
    item_responses: list[PsychoItemResponse]


@dataclass(frozen=True)
class AssessmentFinalizeResult:
    session: PsychoAssessmentSession
    summary: PsychAssessmentSummary
    adaptive_decision: AdaptiveDecision
    profile_state: UserProfileState | None
    report: PsychoReport | None


@dataclass(frozen=True)
class AssessmentProgressMetadata:
    step_index: int
    estimated_total_steps: int
    is_followup: bool
    phase: str
    progress_ratio: float
    can_complete: bool
    session_status: str
    remaining_steps_hint: int


def start_or_resume_assessment_session(
    db: Session,
    *,
    user_id: str,
    assessment_mode: str,
    version: str = "v3",
    device_type: str | None = None,
) -> PsychoAssessmentSession:
    session = (
        db.query(PsychoAssessmentSession)
        .filter(
            PsychoAssessmentSession.user_id == user_id,
            PsychoAssessmentSession.assessment_mode == assessment_mode,
            PsychoAssessmentSession.status.in_(("started", "in_progress", "awaiting_followup")),
        )
        .order_by(PsychoAssessmentSession.created_at.desc())
        .first()
    )
    if session:
        if device_type and not session.device_type:
            session.device_type = device_type
        return session

    session = PsychoAssessmentSession(
        id=f"pas-{uuid.uuid4().hex[:16]}",
        user_id=user_id,
        assessment_mode=assessment_mode,
        status="started",
        version=version,
        device_type=device_type,
        started_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(session)
    db.flush()
    return session


def get_session_for_user(db: Session, *, user_id: str, session_id: str) -> PsychoAssessmentSession | None:
    return (
        db.query(PsychoAssessmentSession)
        .filter(
            PsychoAssessmentSession.id == session_id,
            PsychoAssessmentSession.user_id == user_id,
        )
        .first()
    )


def upsert_session_answer(
    db: Session,
    *,
    session: PsychoAssessmentSession,
    item_id: str,
    answer_value: int | None,
    started_at: datetime | None = None,
    answered_at: datetime | None = None,
    response_time_ms: int | None = None,
    first_answer_value: int | None = None,
    changed_answer_count: int = 0,
    considered_answer_value: int | None = None,
    uncertainty_reason: str | None = None,
    returned_to_question: bool = False,
    skipped: bool = False,
    device_type: str | None = None,
) -> PsychoItemResponse:
    row = (
        db.query(PsychoItemResponse)
        .filter(
            PsychoItemResponse.session_id == session.id,
            PsychoItemResponse.item_id == item_id,
        )
        .first()
    )
    now = datetime.utcnow()
    if row is None:
        row = PsychoItemResponse(
            user_id=session.user_id,
            session_id=session.id,
            item_id=item_id,
            created_at=now,
            device_type=device_type or session.device_type,
        )
        db.add(row)

    if session.status in {"started", "awaiting_followup"}:
        session.status = "in_progress"

    row.answer_value = None if answer_value is None else int(answer_value)
    row.first_answer_value = row.first_answer_value if row.first_answer_value is not None else first_answer_value
    if row.first_answer_value is None and answer_value is not None:
        row.first_answer_value = int(answer_value)
    row.final_answer_value = None if answer_value is None else int(answer_value)
    row.considered_answer_value = (
        None if answer_value is None else int(answer_value)
    ) if considered_answer_value is None else int(considered_answer_value)
    row.changed_answer_count = max(int(row.changed_answer_count or 0), int(changed_answer_count or 0))
    row.response_time_ms = None if response_time_ms is None else int(response_time_ms)
    row.started_at = started_at or row.started_at or now
    row.answered_at = answered_at or now
    row.skipped = bool(skipped)
    row.returned_to_question = bool(returned_to_question or int(row.changed_answer_count or 0) > 0)
    row.uncertainty_reason = uncertainty_reason
    row.device_type = row.device_type or device_type or session.device_type
    db.flush()
    return row


def get_next_public_item(
    db: Session,
    *,
    session: PsychoAssessmentSession,
) -> PsychoItem | None:
    if session.status == "awaiting_followup":
        item_map = _active_item_map(db)
        summary = build_assessment_summary_from_session(db, session_id=session.id, item_map=item_map)
        decision = decide_adaptive_followup(summary, asked_followup_item_ids=summary.answered_followup_item_ids)
        if decision.should_follow_up and decision.followup_item_id:
            return db.get(PsychoItem, decision.followup_item_id)
        followup_item = None
        if followup_item is not None:
            return followup_item
    return _get_next_standard_item(db, session=session)


def finalize_assessment(
    db: Session,
    *,
    session: PsychoAssessmentSession,
    item_map: dict[str, PsychoItem],
) -> AssessmentFinalizeResult:
    if session.status == "completed":
        summary = build_assessment_summary_from_session(db, session_id=session.id, item_map=item_map)
        return AssessmentFinalizeResult(
            session=session,
            summary=summary,
            adaptive_decision=AdaptiveDecision(
                False,
                None,
                None,
                "already_completed",
                len(summary.answered_followup_item_ids),
                MAX_FOLLOWUPS_PER_SESSION,
            ),
            profile_state=db.get(UserProfileState, session.user_id),
            report=get_latest_psychology_report(db, user_id=session.user_id),
        )

    summary = build_assessment_summary_from_session(db, session_id=session.id, item_map=item_map)
    adaptive_decision = (
        decide_adaptive_followup(summary, asked_followup_item_ids=summary.answered_followup_item_ids)
        if session.assessment_mode == STANDARD_ASSESSMENT_MODE
        else AdaptiveDecision(
            False,
            None,
            None,
            "adaptive_followups_disabled_for_non_public_mode",
            len(summary.answered_followup_item_ids),
            MAX_FOLLOWUPS_PER_SESSION,
        )
    )

    if adaptive_decision.should_follow_up:
        session.status = "awaiting_followup"
        session.completed_at = None
        db.flush()
        return AssessmentFinalizeResult(
            session=session,
            summary=summary,
            adaptive_decision=adaptive_decision,
            profile_state=None,
            report=None,
        )

    session.status = "completed"
    session.completed_at = session.completed_at or datetime.utcnow()
    previous_profile_state = db.get(UserProfileState, session.user_id)
    previous_stage = None if previous_profile_state is None else previous_profile_state.stage
    persist_legacy_psycho_score(db, user_id=session.user_id, summary=summary)
    replace_derived_patterns(db, user_id=session.user_id, derived_patterns=summary.derived_patterns)
    report = create_versioned_psychology_report(db, user_id=session.user_id, summary=summary)
    profile_state = sync_profile_state_from_assessment(db, user_id=session.user_id, summary=summary)
    emit_psychology_completion_events(
        db,
        user_id=session.user_id,
        session=session,
        summary=summary,
        report=report,
        profile_state=profile_state,
        previous_stage=previous_stage,
    )
    db.flush()
    return AssessmentFinalizeResult(
        session=session,
        summary=summary,
        adaptive_decision=adaptive_decision,
        profile_state=profile_state,
        report=report,
    )


def ingest_onboarding_responses(
    db: Session,
    *,
    user_id: str,
    item_map: dict[str, PsychoItem],
    answers: dict[str, int],
    response_ms: dict[str, int] | None = None,
    device_type: str | None = None,
    assessment_mode: str = ONBOARDING_ASSESSMENT_MODE,
    version: str = "v3",
) -> AssessmentWriteResult:
    session = start_or_resume_assessment_session(
        db,
        user_id=user_id,
        assessment_mode=assessment_mode,
        version=version,
        device_type=device_type,
    )
    persisted_rows: list[PsychoItemResponse] = []
    now = datetime.utcnow()

    for item_id, answer in answers.items():
        row = upsert_session_answer(
            db,
            session=session,
            item_id=item_id,
            answer_value=int(answer),
            started_at=now,
            answered_at=now,
            response_time_ms=None if response_ms is None else response_ms.get(item_id),
            first_answer_value=int(answer),
            changed_answer_count=0,
            considered_answer_value=int(answer),
            returned_to_question=False,
            skipped=False,
            device_type=device_type,
        )
        persisted_rows.append(row)

    session.status = "completed"
    session.completed_at = now
    db.flush()
    return AssessmentWriteResult(session=session, item_responses=persisted_rows)


def build_assessment_summary_from_session(
    db: Session,
    *,
    session_id: str,
    item_map: dict[str, PsychoItem],
) -> PsychAssessmentSummary:
    session = db.get(PsychoAssessmentSession, session_id)
    if session is None:
        raise KeyError(f"missing_assessment_session:{session_id}")

    rows = (
        db.query(PsychoItemResponse)
        .filter(PsychoItemResponse.session_id == session_id)
        .all()
    )
    normalized = adapt_assessment_item_responses(rows, item_lookup=item_map)
    scored = score_psychology_responses(normalized)
    legacy_traits, legacy_vector, legacy_uncertainty = build_legacy_psycho_score_payload(scored)
    contradiction_summary = scored.scoring_metadata["contradiction_result"]
    timing_summary = scored.scoring_metadata["timing_summary"]
    derived_patterns = derive_patterns(
        scored.traits,
        dict(scored.scoring_metadata["uncertainty_by_trait"]),
        confidence_modifier=contradiction_summary.confidence_modifier,
    )
    answered_followup_item_ids = {item_id for item_id in normalized if is_followup_item(item_id)}
    return PsychAssessmentSummary(
        session=session,
        normalized_responses=normalized,
        scored=scored,
        legacy_traits=legacy_traits,
        legacy_vector=legacy_vector,
        legacy_uncertainty=legacy_uncertainty,
        derived_patterns=derived_patterns,
        timing_summary=timing_summary,
        contradiction_summary=contradiction_summary,
        answered_followup_item_ids=answered_followup_item_ids,
    )


def replace_derived_patterns(
    db: Session,
    *,
    user_id: str,
    derived_patterns: list[DerivedPattern],
) -> None:
    db.query(PsychoDerivedPattern).filter(PsychoDerivedPattern.user_id == user_id).delete()
    now = datetime.utcnow()
    for pattern in derived_patterns:
        db.add(
            PsychoDerivedPattern(
                user_id=user_id,
                pattern_key=pattern.pattern_key,
                pattern_score=pattern.pattern_score,
                confidence=pattern.confidence,
                contributing_dimensions=pattern.contributing_dimensions,
                explanation_internal=pattern.explanation_internal,
                created_at=now,
                updated_at=now,
            )
        )


def persist_legacy_psycho_score(
    db: Session,
    *,
    user_id: str,
    summary: PsychAssessmentSummary,
) -> PsychoScore:
    row = db.get(PsychoScore, user_id)
    if row is None:
        row = PsychoScore(user_id=user_id)
        db.add(row)

    row.o = summary.legacy_traits["O"]
    row.c = summary.legacy_traits["C"]
    row.e = summary.legacy_traits["E"]
    row.a = summary.legacy_traits["A"]
    row.n = summary.legacy_traits["N"]
    row.att_anxiety = summary.legacy_traits["att_anxiety"]
    row.att_avoid = summary.legacy_traits["att_avoid"]
    row.reassurance_need = summary.scored.traits["reassurance_need"]
    row.independence_need = summary.scored.traits["independence_need"]
    row.vulnerability_comfort = summary.scored.traits["vulnerability_comfort"]
    row.conflict_direct = summary.legacy_traits["conflict_direct"]
    row.conflict_avoid = summary.legacy_traits["conflict_avoid"]
    row.conflict_delay = summary.legacy_traits["conflict_delay"]
    row.emotional_regulation = summary.scored.traits["emotional_regulation"]
    row.value_stability = summary.legacy_traits["value_stability"]
    row.value_novelty = summary.legacy_traits["value_novelty"]
    row.aff_attention = summary.legacy_traits["aff_attention"]
    row.aff_touch = summary.scored.traits["aff_touch"]
    row.aff_words = summary.scored.traits["aff_words"]
    row.aff_acts = summary.scored.traits["aff_acts"]
    row.aff_gifts = summary.scored.traits["aff_gifts"]
    row.psycho_vector = summary.legacy_vector
    row.psycho_uncertainty = summary.legacy_uncertainty
    row.quality_flags = {
        **summary.scored.quality_flags,
        "assessment_session_id": summary.session.id,
        "derived_pattern_keys": [pattern.pattern_key for pattern in summary.derived_patterns],
        "adaptive_followups_answered": len(summary.answered_followup_item_ids),
        "canonical_dimension_version": "v2",
        "canonical_dimensions": [
            "reassurance_need",
            "independence_need",
            "vulnerability_comfort",
            "emotional_regulation",
            "aff_touch",
            "aff_words",
            "aff_acts",
            "aff_gifts",
        ],
    }
    row.computed_at = datetime.utcnow()
    db.flush()
    return row


def persist_legacy_psycho_response(
    db: Session,
    *,
    user_id: str,
    item_id: str,
    answer_value: int | None,
    response_time_ms: int | None = None,
    skipped: bool = False,
) -> PsychoResponse | None:
    # Compatibility output only. Canonical public assessment answers now live in
    # PsychoAssessmentSession + PsychoItemResponse. PsychoResponse remains until
    # the legacy onboarding flow and any remaining legacy readers are retired.
    if skipped or answer_value is None:
        return None
    row = db.get(PsychoResponse, {"user_id": user_id, "item_id": item_id})
    if row is None:
        row = PsychoResponse(user_id=user_id, item_id=item_id)
        db.add(row)
    row.answer = int(answer_value)
    row.response_ms = None if response_time_ms is None else int(response_time_ms)
    row.created_at = datetime.utcnow()
    db.flush()
    return row


def sync_profile_state_from_assessment(
    db: Session,
    *,
    user_id: str,
    summary: PsychAssessmentSummary,
) -> UserProfileState:
    user = db.get(User, user_id)
    state = db.get(UserProfileState, user_id)
    if state is None:
        state = UserProfileState(user_id=user_id)
        db.add(state)

    behavior_feature = db.get(BehaviorFeature, user_id)
    behavior_completion = 1.0 if behavior_feature and behavior_feature.behavior_vector else float(state.behavior_completion or 0.0)
    behavior_confidence = 0.7 if behavior_feature and behavior_feature.behavior_vector else float(state.behavior_confidence or 0.0)
    astro_completion = float(state.astro_completion or 0.0)
    astro_confidence = float(state.astro_confidence or 0.0)
    require_astro = preference_requires_astro(user.matching_preference if user else None)
    psycho_uncertainty_avg = sum(summary.legacy_uncertainty) / float(max(1, len(summary.legacy_uncertainty)))

    eligibility = evaluate_eligibility(
        astro_completion=astro_completion,
        psycho_completion=1.0,
        behavior_completion=behavior_completion,
        quality_flags=summary.scored.quality_flags,
        psycho_uncertainty_avg=psycho_uncertainty_avg,
        require_astro=require_astro,
    )

    state.stage = eligibility.stage
    state.psycho_complete = True
    state.required_modules_complete = eligibility.required_modules_complete
    state.quality_pass = eligibility.quality_pass
    state.psycho_completion = eligibility.psycho_completion
    state.behavior_completion = eligibility.behavior_completion
    state.astro_completion = eligibility.astro_completion
    state.psycho_confidence = eligibility.psycho_confidence
    state.behavior_confidence = behavior_confidence
    state.astro_confidence = astro_confidence
    state.overall_confidence = eligibility.overall_confidence
    state.updated_at = datetime.utcnow()
    db.flush()
    return state


def get_latest_report_for_user(db: Session, *, user_id: str) -> PsychoReport | None:
    return get_latest_psychology_report(db, user_id=user_id)


def build_public_progress_metadata(
    db: Session,
    *,
    session: PsychoAssessmentSession,
    next_item: PsychoItem | None = None,
) -> AssessmentProgressMetadata:
    answered_ids = _answered_item_ids(db, session=session)
    standard_ids = {item.id for item in get_standard_item_bank()}
    answered_standard_count = len(answered_ids & standard_ids)
    answered_followup_count = len({item_id for item_id in answered_ids if is_followup_item(item_id)})
    total_answered_count = answered_standard_count + answered_followup_count
    standard_total = len(standard_ids)
    is_followup = bool(next_item and is_followup_item(next_item.id))

    if session.status == "completed":
        estimated_total_steps = max(total_answered_count, 1)
        phase = "completed"
    elif is_followup or session.status == "awaiting_followup":
        estimated_total_steps = standard_total + max(answered_followup_count + 1, 1)
        phase = "clarification"
    else:
        estimated_total_steps = standard_total
        phase = "standard"

    estimated_total_steps = min(standard_total + MAX_FOLLOWUPS_PER_SESSION, max(estimated_total_steps, 1))
    if session.status == "completed":
        progress_ratio = 1.0
        step_index = estimated_total_steps
    else:
        progress_ratio = min(1.0, total_answered_count / float(max(1, estimated_total_steps)))
        step_index = min(estimated_total_steps, total_answered_count + 1)

    remaining_steps_hint = 0 if session.status == "completed" else max(0, estimated_total_steps - total_answered_count)
    return AssessmentProgressMetadata(
        step_index=step_index,
        estimated_total_steps=estimated_total_steps,
        is_followup=is_followup,
        phase=phase,
        progress_ratio=progress_ratio,
        can_complete=total_answered_count > 0 and session.status != "completed",
        session_status=session.status,
        remaining_steps_hint=remaining_steps_hint,
    )


def _get_next_standard_item(db: Session, *, session: PsychoAssessmentSession) -> PsychoItem | None:
    answered_ids = _answered_item_ids(db, session=session)
    for item in get_standard_item_bank():
        if item.id not in answered_ids:
            return db.get(PsychoItem, item.id)
    return None


def _answered_item_ids(db: Session, *, session: PsychoAssessmentSession) -> set[str]:
    return {
        row.item_id
        for row in db.query(PsychoItemResponse)
        .filter(PsychoItemResponse.session_id == session.id)
        .all()
        if row.answer_value is not None or row.final_answer_value is not None or row.considered_answer_value is not None
    }


def _active_item_map(db: Session) -> dict[str, PsychoItem]:
    rows = db.query(PsychoItem).filter(PsychoItem.is_active.is_(True)).all()
    return {row.id: row for row in rows}
