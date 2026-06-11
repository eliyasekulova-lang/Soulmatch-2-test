from __future__ import annotations

from dataclasses import dataclass

from .psychology_response_adapter import NormalizedPsychologyResponse


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class ContradictionMappingResult:
    quality_concerns: list[str]
    meaningful_tensions: list[str]
    contradiction_score: float
    confidence_modifier: float
    pattern_candidates: list[str]


ITEM_CONTRADICTION_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("B5_O_01", "B5_O_02", "openness_inconsistency"),
    ("B5_E_01", "B5_E_02", "social_energy_inconsistency"),
    ("B5_N_01", "B5_N_04", "stress_stability_inconsistency"),
    ("ATT_01", "ATT_08", "attachment_reassurance_inconsistency"),
    ("CON_01", "CON_09", "conflict_approach_inconsistency"),
    ("REG_01", "REG_04", "regulation_stability_inconsistency"),
)


def evaluate_contradictions(
    traits: dict[str, float],
    responses: dict[str, NormalizedPsychologyResponse],
) -> ContradictionMappingResult:
    quality_concerns: list[str] = []
    meaningful_tensions: list[str] = []
    pattern_candidates: list[str] = []

    item_level_hits = 0
    for left_id, right_id, label in ITEM_CONTRADICTION_PAIRS:
        left = _aligned_answer(responses.get(left_id))
        right = _aligned_answer(responses.get(right_id))
        if left is None or right is None:
            continue
        if abs(left - right) >= 0.75:
            item_level_hits += 1
            quality_concerns.append(label)

    if traits.get("reassurance_need", 0.0) >= 0.65 and traits.get("independence_need", 0.0) >= 0.65:
        meaningful_tensions.append("closeness_and_independence_pull")
        pattern_candidates.append("intimacy_pace")

    if traits.get("vulnerability_comfort", 0.0) >= 0.60 and traits.get("att_anxiety", 0.0) >= 0.65:
        meaningful_tensions.append("trust_and_abandonment_tension")
        pattern_candidates.append("relational_security_profile")

    if traits.get("conflict_avoid", 0.0) >= 0.65 and (
        traits.get("N", 0.0) >= 0.60 or traits.get("emotional_regulation", 0.5) <= 0.40
    ):
        meaningful_tensions.append("conflict_avoidance_with_high_reactivity")
        pattern_candidates.append("conflict_repair_style")

    if traits.get("O", 0.0) >= 0.65 and traits.get("value_stability", 0.0) >= 0.65:
        meaningful_tensions.append("exploration_with_stability_pull")
        pattern_candidates.append("stability_vs_exploration_profile")

    if traits.get("A", 0.0) >= 0.65 and traits.get("conflict_direct", 0.0) <= 0.35:
        meaningful_tensions.append("harmony_with_low_directness")
        pattern_candidates.append("conflict_repair_style")

    total_hits = item_level_hits + len(meaningful_tensions)
    contradiction_score = clamp(total_hits / 6.0)
    confidence_modifier = clamp(1.0 - (item_level_hits * 0.12) - (len(meaningful_tensions) * 0.05), 0.45, 1.0)

    return ContradictionMappingResult(
        quality_concerns=quality_concerns,
        meaningful_tensions=meaningful_tensions,
        contradiction_score=contradiction_score,
        confidence_modifier=confidence_modifier,
        pattern_candidates=sorted(set(pattern_candidates)),
    )


def _aligned_answer(row: NormalizedPsychologyResponse | None) -> float | None:
    if row is None or row.skipped:
        return None
    for value in (row.considered_answer_value, row.final_answer_value, row.answer_value, row.first_answer_value):
        if value is None:
            continue
        normalized = (float(value) - 1.0) / 4.0
        return 1.0 - normalized if row.reverse_key else normalized
    return None
