from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.psychology_item_bank import get_followup_item_bank

if TYPE_CHECKING:
    from .assessment_flow_service import PsychAssessmentSummary


MAX_FOLLOWUPS_PER_SESSION = 3

FOLLOWUP_THEME_ITEM_MAP = {
    "closeness_independence_tension": "FUP_ATT_01",
    "trust_abandonment_tension": "FUP_ATT_02",
    "conflict_reactivity_tension": "FUP_CON_01",
    "hesitation_clarification": "FUP_REG_01",
    "stability_novelty_tension": "FUP_VAL_01",
    "agreeableness_directness_tension": "FUP_DIR_01",
}


@dataclass(frozen=True)
class AdaptiveDecision:
    should_follow_up: bool
    followup_item_id: str | None
    followup_theme: str | None
    reason: str | None
    followup_count: int
    max_followups: int


def decide_adaptive_followup(
    summary: PsychAssessmentSummary,
    *,
    asked_followup_item_ids: set[str],
) -> AdaptiveDecision:
    followup_count = len(asked_followup_item_ids)
    if followup_count >= MAX_FOLLOWUPS_PER_SESSION:
        return AdaptiveDecision(False, None, None, "followup_cap_reached", followup_count, MAX_FOLLOWUPS_PER_SESSION)

    scored = summary.scored
    timing = scored.scoring_metadata["timing_summary"]
    contradiction = scored.scoring_metadata["contradiction_result"]
    uncertainty_by_trait = dict(scored.scoring_metadata["uncertainty_by_trait"])

    candidate_themes: list[tuple[str, str]] = []
    meaningful_tensions = set(contradiction.meaningful_tensions)
    if "closeness_and_independence_pull" in meaningful_tensions:
        candidate_themes.append(("closeness_independence_tension", "clarify_closeness_vs_independence"))
    if "trust_and_abandonment_tension" in meaningful_tensions:
        candidate_themes.append(("trust_abandonment_tension", "clarify_trust_vs_reassurance"))
    if "conflict_avoidance_with_high_reactivity" in meaningful_tensions:
        candidate_themes.append(("conflict_reactivity_tension", "clarify_conflict_reactivity"))
    if "exploration_with_stability_pull" in meaningful_tensions:
        candidate_themes.append(("stability_novelty_tension", "clarify_stability_vs_novelty"))
    if "harmony_with_low_directness" in meaningful_tensions:
        candidate_themes.append(("agreeableness_directness_tension", "clarify_harmony_vs_directness"))

    if timing.hesitation_score >= 0.45 or timing.ambivalence_score >= 0.4 or timing.change_signal >= 0.35:
        candidate_themes.append(("hesitation_clarification", "recover_confidence_after_hesitation"))

    low_confidence_priority = [
        ("att_anxiety", "trust_abandonment_tension", "recover_attachment_confidence"),
        ("independence_need", "closeness_independence_tension", "recover_attachment_pacing_confidence"),
        ("conflict_direct", "agreeableness_directness_tension", "recover_directness_confidence"),
        ("emotional_regulation", "hesitation_clarification", "recover_regulation_confidence"),
        ("value_stability", "stability_novelty_tension", "recover_values_confidence"),
    ]
    for trait_key, theme, reason in low_confidence_priority:
        if uncertainty_by_trait.get(trait_key, 0.0) >= 0.45:
            candidate_themes.append((theme, reason))

    for theme, reason in candidate_themes:
        item_id = FOLLOWUP_THEME_ITEM_MAP[theme]
        if item_id not in asked_followup_item_ids:
            return AdaptiveDecision(True, item_id, theme, reason, followup_count, MAX_FOLLOWUPS_PER_SESSION)

    return AdaptiveDecision(False, None, None, "no_additional_followup_needed", followup_count, MAX_FOLLOWUPS_PER_SESSION)


def get_followup_item_ids() -> set[str]:
    return {item.id for item in get_followup_item_bank()}
