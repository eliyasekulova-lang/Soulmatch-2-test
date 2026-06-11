from __future__ import annotations

from dataclasses import dataclass

from .psychology_response_adapter import build_normalized_response
from .psychology_scoring_service import (
    build_legacy_psycho_score_payload,
    clamp,
    norm_1_5,
    reverse_likert,
    score_psychology_responses,
)


@dataclass
class ScoredPsych:
    traits: dict[str, float]
    vector: list[float]
    uncertainty: list[float]
    quality_flags: dict[str, object]


PSY_VECTOR_ORDER = [
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
    "reserved",
]


def score_psychometrics(
    answers: dict[str, tuple[int, bool, str, float]],
    response_ms: dict[str, int] | None = None,
) -> ScoredPsych:
    normalized = {}
    for item_id, (answer, reverse_key, trait_key, weight) in answers.items():
        normalized[item_id] = build_normalized_response(
            item_id=item_id,
            answer_value=int(answer),
            first_answer_value=int(answer),
            final_answer_value=int(answer),
            considered_answer_value=int(answer),
            changed_answer_count=0,
            response_time_ms=None if response_ms is None else response_ms.get(item_id),
            returned_to_question=False,
            skipped=False,
            reverse_key=reverse_key,
            trait_key=trait_key,
            weight=weight,
        )

    scored = score_psychology_responses(normalized)
    legacy_traits, vector, uncertainty = build_legacy_psycho_score_payload(scored)

    quality_flags = dict(scored.quality_flags)
    quality_flags["inconsistent_pairs"] = len(scored.scoring_metadata["contradiction_result"].quality_concerns)

    return ScoredPsych(
        traits=legacy_traits,
        vector=vector,
        uncertainty=uncertainty,
        quality_flags=quality_flags,
    )
