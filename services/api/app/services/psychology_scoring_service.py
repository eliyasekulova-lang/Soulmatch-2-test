from __future__ import annotations

from dataclasses import dataclass

from app.psychology_item_bank import get_target_item_counts

from .contradiction_mapping_service import ContradictionMappingResult, evaluate_contradictions
from .psychology_response_adapter import NormalizedPsychologyResponse
from .response_timing_service import ResponseTimingSummary, analyze_response_timing


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def reverse_likert(answer: int) -> int:
    return 6 - answer


def norm_1_5(value: float) -> float:
    return (value - 1.0) / 4.0


PSYCH_VECTOR_ORDER = [
    "O",
    "C",
    "E",
    "A",
    "N",
    "att_anxiety",
    "att_avoid",
    "reassurance_need",
    "independence_need",
    "vulnerability_comfort",
    "conflict_direct",
    "conflict_avoid",
    "conflict_delay",
    "emotional_regulation",
    "value_stability",
    "value_novelty",
    "aff_attention",
    "aff_touch",
    "aff_words",
    "aff_acts",
    "aff_gifts",
]


@dataclass(frozen=True)
class PsychologyScoreResult:
    traits: dict[str, float]
    vector: list[float]
    uncertainty: list[float]
    quality_flags: dict[str, object]
    dimension_counts: dict[str, int]
    scoring_metadata: dict[str, object]


LEGACY_PSYCHO_SCORE_KEYS = [
    "O",
    "C",
    "E",
    "A",
    "N",
    "att_anxiety",
    "att_avoid",
    "conflict_direct",
    "conflict_avoid",
    "conflict_delay",
    "value_stability",
    "value_novelty",
    "aff_attention",
]


def score_psychology_responses(
    responses: dict[str, NormalizedPsychologyResponse],
) -> PsychologyScoreResult:
    target_item_counts = get_target_item_counts()
    buckets: dict[str, list[float]] = {}
    raw_answers: list[int] = []
    dimension_counts: dict[str, int] = {}

    for item_id, row in responses.items():
        answer = _resolved_answer(row)
        if row.skipped or answer is None or answer < 1 or answer > 5:
            continue
        transformed = reverse_likert(answer) if row.reverse_key else answer
        weighted_value = float(transformed) * float(row.weight)
        buckets.setdefault(row.trait_key, []).append(weighted_value)
        dimension_counts[row.trait_key] = dimension_counts.get(row.trait_key, 0) + 1
        raw_answers.append(int(answer))

    traits: dict[str, float] = {}
    uncertainty_by_trait: dict[str, float] = {}
    for key in PSYCH_VECTOR_ORDER:
        values = buckets.get(key, [])
        mean_value = sum(values) / max(1, len(values)) if values else 3.0
        traits[key] = clamp(norm_1_5(mean_value))

        target = target_item_counts.get(key, 1)
        coverage_ratio = min(dimension_counts.get(key, 0) / float(max(1, target)), 1.0)
        uncertainty_by_trait[key] = clamp(1.0 - coverage_ratio)

    timing_summary = analyze_response_timing(responses.values())
    contradiction_result = evaluate_contradictions(traits, responses)

    global_uncertainty_lift = clamp(
        ((1.0 - timing_summary.timing_confidence) * 0.45)
        + (timing_summary.ambivalence_score * 0.20)
        + ((1.0 - contradiction_result.confidence_modifier) * 0.35)
    )
    for key in uncertainty_by_trait:
        uncertainty_by_trait[key] = clamp(
            (uncertainty_by_trait[key] * 0.7) + (global_uncertainty_lift * 0.3)
        )

    quality_flags = _build_quality_flags(raw_answers, timing_summary, contradiction_result, responses)
    vector = [traits[key] for key in PSYCH_VECTOR_ORDER]
    uncertainty = [uncertainty_by_trait[key] for key in PSYCH_VECTOR_ORDER]

    scoring_metadata = {
        "vector_order": PSYCH_VECTOR_ORDER,
        "uncertainty_by_trait": uncertainty_by_trait,
        "target_item_counts": target_item_counts,
        "timing_summary": timing_summary,
        "contradiction_result": contradiction_result,
        "answered_item_count": sum(dimension_counts.values()),
    }

    return PsychologyScoreResult(
        traits=traits,
        vector=vector,
        uncertainty=uncertainty,
        quality_flags=quality_flags,
        dimension_counts=dimension_counts,
        scoring_metadata=scoring_metadata,
    )


def build_legacy_psycho_score_payload(scored: PsychologyScoreResult) -> tuple[dict[str, float], list[float], list[float]]:
    vector_order = list(scored.scoring_metadata["vector_order"])
    uncertainty_by_trait = dict(scored.scoring_metadata["uncertainty_by_trait"])
    legacy_traits = {key: scored.traits.get(key, 0.5) for key in LEGACY_PSYCHO_SCORE_KEYS}
    legacy_vector = [legacy_traits[key] for key in LEGACY_PSYCHO_SCORE_KEYS] + [0.5]
    legacy_uncertainty = [uncertainty_by_trait.get(key, 1.0) for key in LEGACY_PSYCHO_SCORE_KEYS] + [1.0]
    return legacy_traits, legacy_vector, legacy_uncertainty


def _build_quality_flags(
    raw_answers: list[int],
    timing_summary: ResponseTimingSummary,
    contradiction_result: ContradictionMappingResult,
    responses: dict[str, NormalizedPsychologyResponse],
) -> dict[str, object]:
    flags: dict[str, object] = {
        "speeding": timing_summary.speeding_flag,
        "straight_lining": False,
        "median_response_ms": timing_summary.median_response_ms,
        "hesitation_score": round(timing_summary.hesitation_score, 4),
        "ambivalence_score": round(timing_summary.ambivalence_score, 4),
        "reflection_score": round(timing_summary.reflection_score, 4),
        "change_signal": round(timing_summary.change_signal, 4),
        "return_signal": round(timing_summary.return_signal, 4),
        "contradiction_score": round(contradiction_result.contradiction_score, 4),
        "quality_concerns": contradiction_result.quality_concerns,
        "meaningful_tensions": contradiction_result.meaningful_tensions,
        "skipped_items": sum(1 for row in responses.values() if row.skipped),
    }
    if raw_answers:
        most_common = max(raw_answers.count(i) for i in range(1, 6))
        flags["straight_lining"] = len(raw_answers) >= 12 and (most_common / float(len(raw_answers))) >= 0.8
    return flags


def _resolved_answer(row: NormalizedPsychologyResponse) -> int | None:
    for value in (row.considered_answer_value, row.final_answer_value, row.answer_value, row.first_answer_value):
        if value is not None:
            return int(value)
    return None
