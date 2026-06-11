from types import SimpleNamespace

from app.services.adaptive_assessment_service import decide_adaptive_followup


def _summary(
    *,
    meaningful_tensions: list[str] | None = None,
    hesitation_score: float = 0.0,
    ambivalence_score: float = 0.0,
    change_signal: float = 0.0,
    uncertainty_by_trait: dict[str, float] | None = None,
    answered_followup_item_ids: set[str] | None = None,
):
    return SimpleNamespace(
        scored=SimpleNamespace(
            scoring_metadata={
                "timing_summary": SimpleNamespace(
                    hesitation_score=hesitation_score,
                    ambivalence_score=ambivalence_score,
                    change_signal=change_signal,
                ),
                "contradiction_result": SimpleNamespace(
                    meaningful_tensions=meaningful_tensions or [],
                ),
                "uncertainty_by_trait": uncertainty_by_trait or {},
            }
        ),
        answered_followup_item_ids=answered_followup_item_ids or set(),
    )


def test_adaptive_service_prioritizes_meaningful_tensions():
    decision = decide_adaptive_followup(
        _summary(meaningful_tensions=["closeness_and_independence_pull"]),
        asked_followup_item_ids=set(),
    )
    assert decision.should_follow_up is True
    assert decision.followup_item_id == "FUP_ATT_01"


def test_adaptive_service_uses_hesitation_recovery_when_needed():
    decision = decide_adaptive_followup(
        _summary(hesitation_score=0.5, ambivalence_score=0.45, change_signal=0.4),
        asked_followup_item_ids=set(),
    )
    assert decision.should_follow_up is True
    assert decision.followup_item_id == "FUP_REG_01"


def test_adaptive_service_caps_followups():
    decision = decide_adaptive_followup(
        _summary(meaningful_tensions=["trust_and_abandonment_tension"]),
        asked_followup_item_ids={"FUP_ATT_01", "FUP_ATT_02", "FUP_CON_01"},
    )
    assert decision.should_follow_up is False
    assert decision.reason == "followup_cap_reached"
