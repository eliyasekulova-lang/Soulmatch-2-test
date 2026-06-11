from __future__ import annotations

from dataclasses import dataclass


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class DerivedPattern:
    pattern_key: str
    pattern_score: float
    confidence: float
    contributing_dimensions: dict[str, float]
    explanation_internal: str


def derive_patterns(
    traits: dict[str, float],
    uncertainty_by_trait: dict[str, float],
    *,
    confidence_modifier: float = 1.0,
) -> list[DerivedPattern]:
    patterns = [
        _build_pattern(
            "emotional_reactivity_profile",
            {
                "N": traits.get("N", 0.5),
                "att_anxiety": traits.get("att_anxiety", 0.5),
                "low_emotional_regulation": 1.0 - traits.get("emotional_regulation", 0.5),
            },
            uncertainty_by_trait,
            confidence_modifier,
            "Combines emotional sensitivity, reassurance pull, and recovery steadiness.",
        ),
        _build_pattern(
            "relational_security_profile",
            {
                "low_att_anxiety": 1.0 - traits.get("att_anxiety", 0.5),
                "low_att_avoid": 1.0 - traits.get("att_avoid", 0.5),
                "vulnerability_comfort": traits.get("vulnerability_comfort", 0.5),
            },
            uncertainty_by_trait,
            confidence_modifier,
            "Tracks steadiness in closeness, openness, and comfort with reliance.",
        ),
        _build_pattern(
            "conflict_repair_style",
            {
                "conflict_direct": traits.get("conflict_direct", 0.5),
                "low_conflict_avoid": 1.0 - traits.get("conflict_avoid", 0.5),
                "emotional_regulation": traits.get("emotional_regulation", 0.5),
                "A": traits.get("A", 0.5),
            },
            uncertainty_by_trait,
            confidence_modifier,
            "Summarizes how directly and steadily someone tends to repair tension.",
        ),
        _build_pattern(
            "intimacy_pace",
            {
                "vulnerability_comfort": traits.get("vulnerability_comfort", 0.5),
                "low_independence_need": 1.0 - traits.get("independence_need", 0.5),
                "low_conflict_delay": 1.0 - traits.get("conflict_delay", 0.5),
            },
            uncertainty_by_trait,
            confidence_modifier,
            "Represents how readily closeness tends to build once trust is present.",
        ),
        _build_pattern(
            "stability_vs_exploration_profile",
            {
                "O": traits.get("O", 0.5),
                "value_novelty": traits.get("value_novelty", 0.5),
                "low_value_stability": 1.0 - traits.get("value_stability", 0.5),
            },
            uncertainty_by_trait,
            confidence_modifier,
            "Captures the relative pull between familiarity and exploration.",
        ),
    ]
    return patterns


def _build_pattern(
    pattern_key: str,
    contributing_dimensions: dict[str, float],
    uncertainty_by_trait: dict[str, float],
    confidence_modifier: float,
    explanation_internal: str,
) -> DerivedPattern:
    values = list(contributing_dimensions.values())
    pattern_score = clamp(sum(values) / float(len(values) or 1))

    relevant_uncertainties = []
    for key in contributing_dimensions:
        base_key = key
        if key.startswith("low_"):
            base_key = key[4:]
        relevant_uncertainties.append(uncertainty_by_trait.get(base_key, 0.5))

    confidence = clamp((1.0 - (sum(relevant_uncertainties) / float(len(relevant_uncertainties) or 1))) * confidence_modifier)
    return DerivedPattern(
        pattern_key=pattern_key,
        pattern_score=pattern_score,
        confidence=confidence,
        contributing_dimensions=contributing_dimensions,
        explanation_internal=explanation_internal,
    )
