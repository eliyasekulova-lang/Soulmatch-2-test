from __future__ import annotations

from dataclasses import dataclass

from .psycho_scoring import clamp


@dataclass
class EligibilityResult:
    stage: str
    required_modules_complete: bool
    quality_pass: bool
    eligibility_score: float
    astro_completion: float
    psycho_completion: float
    behavior_completion: float
    astro_confidence: float
    psycho_confidence: float
    behavior_confidence: float
    overall_confidence: float


def _normalize_weighted_score(values: dict[str, float], weights: dict[str, float]) -> float:
    active_weight = sum(weight for key, weight in weights.items() if key in values)
    if active_weight <= 0:
        return 0.0
    total = sum(clamp(values[key]) * weight for key, weight in weights.items() if key in values)
    return clamp(total / active_weight)


def evaluate_eligibility(
    astro_completion: float,
    psycho_completion: float,
    behavior_completion: float,
    quality_flags: dict[str, object],
    psycho_uncertainty_avg: float,
    require_astro: bool = True,
) -> EligibilityResult:
    straight_lining = bool(quality_flags.get("straight_lining", False))
    speeding = bool(quality_flags.get("speeding", False))
    inconsistent_pairs = int(quality_flags.get("inconsistent_pairs", 0) or 0)
    quality_pass = (not straight_lining) and (not speeding) and inconsistent_pairs <= 1

    completion_values = {
        "psycho": psycho_completion,
        "behavior": behavior_completion,
    }
    completion_weights = {
        "psycho": 0.5,
        "behavior": 0.2,
    }
    if require_astro:
        completion_values["astro"] = astro_completion
        completion_weights["astro"] = 0.3
    eligibility_score = _normalize_weighted_score(completion_values, completion_weights)
    required_modules_complete = psycho_completion >= 1.0 and ((not require_astro) or astro_completion >= 1.0)

    psycho_confidence = clamp(1.0 - psycho_uncertainty_avg)
    astro_confidence = clamp(astro_completion)
    behavior_confidence = clamp(behavior_completion)

    confidence_values = {
        "psycho": psycho_confidence,
        "behavior": behavior_confidence,
    }
    confidence_weights = {
        "psycho": 0.45,
        "behavior": 0.30,
    }
    if require_astro:
        confidence_values["astro"] = astro_confidence
        confidence_weights["astro"] = 0.25
    overall_confidence = _normalize_weighted_score(confidence_values, confidence_weights)

    if not required_modules_complete:
        stage = "incomplete"
    elif quality_pass and eligibility_score >= 0.75:
        stage = "eligible"
    else:
        stage = "calibrating"

    return EligibilityResult(
        stage=stage,
        required_modules_complete=required_modules_complete,
        quality_pass=quality_pass,
        eligibility_score=eligibility_score,
        astro_completion=astro_completion,
        psycho_completion=psycho_completion,
        behavior_completion=behavior_completion,
        astro_confidence=astro_confidence,
        psycho_confidence=psycho_confidence,
        behavior_confidence=behavior_confidence,
        overall_confidence=overall_confidence,
    )
