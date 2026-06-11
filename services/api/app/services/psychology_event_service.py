from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models import AnalyticsEvent, PsychoAssessmentSession, PsychoReport, UserProfileState

if TYPE_CHECKING:
    from .assessment_flow_service import PsychAssessmentSummary


@dataclass(frozen=True)
class PsychologyEventDispatchResult:
    event_names: list[str]


def emit_psychology_completion_events(
    db: Session,
    *,
    user_id: str,
    session: PsychoAssessmentSession,
    summary: "PsychAssessmentSummary",
    report: PsychoReport,
    profile_state: UserProfileState | None,
    previous_stage: str | None,
) -> PsychologyEventDispatchResult:
    event_names: list[str] = []
    base_payload = {
        "session_id": session.id,
        "assessment_mode": session.assessment_mode,
        "report_version": report.report_version,
        "derived_pattern_count": len(summary.derived_patterns),
        "followup_count": len(summary.answered_followup_item_ids),
    }

    event_names.append(_add_event(db, user_id=user_id, event_name="psychology_assessment_completed", event_payload=base_payload))
    event_names.append(
        _add_event(
            db,
            user_id=user_id,
            event_name="psychology_report_generated",
            event_payload={**base_payload, "session_report_linked": bool(report.session_id)},
        )
    )
    event_names.append(
        _add_event(
            db,
            user_id=user_id,
            event_name="psychology_profile_updated",
            event_payload={
                **base_payload,
                "psycho_confidence": None if profile_state is None else float(profile_state.psycho_confidence or 0.0),
                "overall_confidence": None if profile_state is None else float(profile_state.overall_confidence or 0.0),
            },
        )
    )

    if profile_state is not None and previous_stage != profile_state.stage:
        event_names.append(
            _add_event(
                db,
                user_id=user_id,
                event_name="psychology_profile_milestone_advanced",
                event_payload={
                    **base_payload,
                    "previous_stage": previous_stage,
                    "new_stage": profile_state.stage,
                },
            )
        )

    event_names.append(
        _add_event(
            db,
            user_id=user_id,
            event_name="psychology_compatibility_refresh_requested",
            event_payload={
                **base_payload,
                "profile_stage": None if profile_state is None else profile_state.stage,
            },
        )
    )
    return PsychologyEventDispatchResult(event_names=event_names)


def _add_event(
    db: Session,
    *,
    user_id: str,
    event_name: str,
    event_payload: dict,
) -> str:
    db.add(AnalyticsEvent(user_id=user_id, event_name=event_name, event_payload=event_payload))
    return event_name
