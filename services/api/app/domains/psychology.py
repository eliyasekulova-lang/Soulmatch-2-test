from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuthUser, PsychoItem
from ..security import get_current_auth_user
from ..services.assessment_flow_service import (
    STANDARD_ASSESSMENT_MODE,
    build_public_progress_metadata,
    finalize_assessment,
    get_latest_report_for_user,
    get_next_public_item,
    get_session_for_user,
    start_or_resume_assessment_session,
    upsert_session_answer,
)
from ..services.psychology_report_service import get_psychology_report_history

router = APIRouter(prefix="/psychology", tags=["psychology"])


class AssessmentItemResponse(BaseModel):
    id: str
    prompt: str
    item_type: str
    module: str
    version: str


class AssessmentStartResponse(BaseModel):
    session_id: str
    assessment_mode: str
    first_item: AssessmentItemResponse | None
    version: str
    progress: "AssessmentProgressResponse"


class AssessmentAnswerRequest(BaseModel):
    session_id: str
    item_id: str
    answer_value: int | None = Field(default=None, ge=1, le=5)
    started_at: datetime | None = None
    answered_at: datetime | None = None
    response_time_ms: int | None = Field(default=None, ge=0)
    first_answer_value: int | None = Field(default=None, ge=1, le=5)
    changed_answer_count: int = Field(default=0, ge=0)
    considered_answer_value: int | None = Field(default=None, ge=1, le=5)
    uncertainty_reason: str | None = Field(default=None, max_length=255)
    returned_to_question: bool = False
    skipped: bool = False


class AssessmentAnswerResponse(BaseModel):
    ok: bool
    session_id: str
    item_id: str
    status: str
    saved_answer_value: int | None
    changed_answer_count: int
    returned_to_question: bool
    skipped: bool
    next_item: AssessmentItemResponse | None = None
    progress: "AssessmentProgressResponse"


class AssessmentNextResponse(BaseModel):
    session_id: str
    status: str
    next_item: AssessmentItemResponse | None
    progress: "AssessmentProgressResponse"


class AssessmentCompleteRequest(BaseModel):
    session_id: str


class AssessmentCompleteResponse(BaseModel):
    ok: bool
    session_id: str
    completion_status: str
    answered_item_count: int
    derived_pattern_count: int
    report_available: bool
    next_item: AssessmentItemResponse | None = None
    followup_count: int = 0
    followup_cap: int = 0
    personality_summary: str | None = None
    confidence_summary: str | None = None
    progress: "AssessmentProgressResponse"


class PsychologyReportResponse(BaseModel):
    session_id: str | None = None
    report_version: str
    personality_summary: str
    relationship_style: str
    conflict_style: str
    attachment_style: str
    affection_needs: str
    blind_spots: str
    best_match_type: str
    growth_suggestions: str
    confidence_summary: str


class PsychologyReportHistoryEntry(BaseModel):
    session_id: str | None = None
    report_version: str
    created_at: datetime
    is_current: bool
    personality_summary: str
    confidence_summary: str


class PsychologyReportHistoryResponse(BaseModel):
    reports: list[PsychologyReportHistoryEntry]


class AssessmentProgressResponse(BaseModel):
    step_index: int
    estimated_total_steps: int
    is_followup: bool
    phase: str
    progress_ratio: float
    can_complete: bool
    session_status: str
    remaining_steps_hint: int


def _serialize_item(item: PsychoItem | None) -> AssessmentItemResponse | None:
    if item is None:
        return None
    return AssessmentItemResponse(
        id=item.id,
        prompt=item.prompt,
        item_type=item.item_type,
        module=item.module,
        version=item.version,
    )


def _get_item_map(db: Session) -> dict[str, PsychoItem]:
    rows = db.query(PsychoItem).filter(PsychoItem.is_active.is_(True)).all()
    return {row.id: row for row in rows}


def _serialize_progress(progress) -> AssessmentProgressResponse:
    return AssessmentProgressResponse(
        step_index=progress.step_index,
        estimated_total_steps=progress.estimated_total_steps,
        is_followup=progress.is_followup,
        phase=progress.phase,
        progress_ratio=progress.progress_ratio,
        can_complete=progress.can_complete,
        session_status=progress.session_status,
        remaining_steps_hint=progress.remaining_steps_hint,
    )


@router.post("/assessment/start", response_model=AssessmentStartResponse)
def start_assessment(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    # Public psychology flow allows one active standard session per user.
    # Start resumes an in-flight session before creating a new one.
    session = start_or_resume_assessment_session(
        db,
        user_id=current_user.id,
        assessment_mode=STANDARD_ASSESSMENT_MODE,
        version="v3",
    )
    next_item = get_next_public_item(db, session=session)
    progress = build_public_progress_metadata(db, session=session, next_item=next_item)
    db.commit()
    return AssessmentStartResponse(
        session_id=session.id,
        assessment_mode=session.assessment_mode,
        first_item=_serialize_item(next_item),
        version=session.version,
        progress=_serialize_progress(progress),
    )


@router.post("/assessment/answer", response_model=AssessmentAnswerResponse)
def submit_assessment_answer(
    payload: AssessmentAnswerRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    session = get_session_for_user(db, user_id=current_user.id, session_id=payload.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assessment_session_not_found")
    if session.status == "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="assessment_session_completed")

    item = db.get(PsychoItem, payload.item_id)
    if item is None or not item.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assessment_item_not_found")

    row = upsert_session_answer(
        db,
        session=session,
        item_id=payload.item_id,
        answer_value=payload.answer_value,
        started_at=payload.started_at,
        answered_at=payload.answered_at,
        response_time_ms=payload.response_time_ms,
        first_answer_value=payload.first_answer_value,
        changed_answer_count=payload.changed_answer_count,
        considered_answer_value=payload.considered_answer_value,
        uncertainty_reason=payload.uncertainty_reason,
        returned_to_question=payload.returned_to_question,
        skipped=payload.skipped,
    )
    next_item = get_next_public_item(db, session=session)
    progress = build_public_progress_metadata(db, session=session, next_item=next_item)
    db.commit()
    return AssessmentAnswerResponse(
        ok=True,
        session_id=session.id,
        item_id=row.item_id,
        status=session.status,
        saved_answer_value=row.final_answer_value,
        changed_answer_count=row.changed_answer_count,
        returned_to_question=row.returned_to_question,
        skipped=row.skipped,
        next_item=_serialize_item(next_item),
        progress=_serialize_progress(progress),
    )


@router.get("/assessment/next", response_model=AssessmentNextResponse)
def get_assessment_next(
    session_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    session = get_session_for_user(db, user_id=current_user.id, session_id=session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assessment_session_not_found")
    if session.status == "completed":
        progress = build_public_progress_metadata(db, session=session, next_item=None)
        return AssessmentNextResponse(
            session_id=session.id,
            status=session.status,
            next_item=None,
            progress=_serialize_progress(progress),
        )

    next_item = get_next_public_item(db, session=session)
    progress = build_public_progress_metadata(db, session=session, next_item=next_item)
    return AssessmentNextResponse(
        session_id=session.id,
        status=session.status,
        next_item=_serialize_item(next_item),
        progress=_serialize_progress(progress),
    )


@router.post("/assessment/complete", response_model=AssessmentCompleteResponse)
def complete_assessment(
    payload: AssessmentCompleteRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    session = get_session_for_user(db, user_id=current_user.id, session_id=payload.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assessment_session_not_found")

    item_map = _get_item_map(db)
    result = finalize_assessment(db, session=session, item_map=item_map)
    report = get_latest_report_for_user(db, user_id=current_user.id)
    next_item = None
    if result.session.status == "awaiting_followup" and result.adaptive_decision.followup_item_id:
        next_item = db.get(PsychoItem, result.adaptive_decision.followup_item_id)
    progress = build_public_progress_metadata(db, session=result.session, next_item=next_item)
    db.commit()
    return AssessmentCompleteResponse(
        ok=True,
        session_id=session.id,
        completion_status=result.session.status,
        answered_item_count=int(result.summary.scored.scoring_metadata.get("answered_item_count", 0)),
        derived_pattern_count=len(result.summary.derived_patterns),
        report_available=report is not None,
        next_item=_serialize_item(next_item),
        followup_count=result.adaptive_decision.followup_count,
        followup_cap=result.adaptive_decision.max_followups,
        personality_summary=None if report is None else report.personality_summary,
        confidence_summary=None if report is None else report.confidence_summary,
        progress=_serialize_progress(progress),
    )


@router.get("/report/me", response_model=PsychologyReportResponse)
def get_my_psychology_report(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    report = get_latest_report_for_user(db, user_id=current_user.id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="psychology_report_not_ready")
    return PsychologyReportResponse(
        session_id=report.session_id,
        report_version=report.report_version,
        personality_summary=report.personality_summary,
        relationship_style=report.relationship_style,
        conflict_style=report.conflict_style,
        attachment_style=report.attachment_style,
        affection_needs=report.affection_needs,
        blind_spots=report.blind_spots,
        best_match_type=report.best_match_type,
        growth_suggestions=report.growth_suggestions,
        confidence_summary=report.confidence_summary,
    )


@router.get("/report/history", response_model=PsychologyReportHistoryResponse)
def get_my_psychology_report_history(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    reports = get_psychology_report_history(db, user_id=current_user.id)
    if not reports:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="psychology_report_not_ready")
    current_report_id = reports[0].id
    return PsychologyReportHistoryResponse(
        reports=[
            PsychologyReportHistoryEntry(
                session_id=report.session_id,
                report_version=report.report_version,
                created_at=report.created_at,
                is_current=report.id == current_report_id,
                personality_summary=report.personality_summary,
                confidence_summary=report.confidence_summary,
            )
            for report in reports
        ]
    )
