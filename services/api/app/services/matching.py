from __future__ import annotations

from dataclasses import dataclass
import math

from .compatibility_dynamics_service import CompatibilityDynamicsResult
from .psycho_scoring import clamp

PSY_ORDER = [
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
IDX = {key: i for i, key in enumerate(PSY_ORDER)}


@dataclass
class PairScore:
    psycho_score: float
    astro_score: float
    behavior_score: float
    final_score: float
    confidence: float
    explanation: dict[str, object]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def mean_abs_diff(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.5
    return sum(abs(x - y) for x, y in zip(a, b)) / float(len(a))


def psycho_similarity_weighted(
    p_a: list[float],
    p_b: list[float],
    u_a: list[float],
    u_b: list[float],
    weights: list[float],
) -> float:
    if not p_a or not p_b:
        return 0.5
    w_eff = []
    for i, weight in enumerate(weights):
        u_avg = (u_a[i] + u_b[i]) / 2.0 if i < len(u_a) and i < len(u_b) else 1.0
        w_eff.append(weight * (1.0 - u_avg))

    a_weighted = [p_a[i] * w_eff[i] for i in range(min(len(p_a), len(w_eff)))]
    b_weighted = [p_b[i] * w_eff[i] for i in range(min(len(p_b), len(w_eff)))]
    cos = cosine_similarity(a_weighted, b_weighted)
    return clamp((cos + 1.0) / 2.0)


def conflict_adjust(p_a: list[float], p_b: list[float]) -> float:
    if not p_a or not p_b:
        return 0.0
    avoid_a = p_a[IDX["conflict_avoid"]]
    avoid_b = p_b[IDX["conflict_avoid"]]
    direct_a = p_a[IDX["conflict_direct"]]
    direct_b = p_b[IDX["conflict_direct"]]
    delay_a = p_a[IDX["conflict_delay"]]
    delay_b = p_b[IDX["conflict_delay"]]

    penalty = 0.0
    if avoid_a > 0.8 and avoid_b > 0.8:
        penalty += 0.08
    if abs(delay_a - delay_b) > 0.7 and min(direct_a, direct_b) < 0.3:
        penalty += 0.06
    return penalty


def dynamic_weights(behavior_confidence: float, include_astro: bool = True) -> tuple[float, float, float]:
    behavior_weight = 0.2 + (0.25 * behavior_confidence)
    psycho_weight = 0.5 - (0.15 * behavior_confidence)
    astro_weight = 1.0 - behavior_weight - psycho_weight
    if include_astro:
        return clamp(psycho_weight), clamp(astro_weight), clamp(behavior_weight)
    active_total = max(0.0001, psycho_weight + behavior_weight)
    return clamp(psycho_weight / active_total), 0.0, clamp(behavior_weight / active_total)


def score_pair(
    p_a: list[float],
    p_b: list[float],
    u_a: list[float],
    u_b: list[float],
    astro_a: list[float],
    astro_b: list[float],
    behavior_a: list[float],
    behavior_b: list[float],
    psycho_confidence: float,
    astro_confidence: float,
    behavior_confidence: float,
    quality_flags: dict[str, object],
    include_astro: bool = True,
    dynamics: CompatibilityDynamicsResult | None = None,
) -> PairScore:
    weights = [1.0] * len(p_a)
    for key in [
        "att_anxiety",
        "att_avoid",
        "conflict_direct",
        "conflict_avoid",
        "conflict_delay",
        "value_stability",
        "value_novelty",
    ]:
        if IDX[key] < len(weights):
            weights[IDX[key]] = 1.35

    base_psycho_score = psycho_similarity_weighted(p_a, p_b, u_a, u_b, weights)
    base_psycho_score = clamp(base_psycho_score - conflict_adjust(p_a, p_b))
    dynamics_score = 0.5 if dynamics is None else dynamics.overall_dynamics_score
    psycho_score = clamp((base_psycho_score * 0.55) + (dynamics_score * 0.45))

    astro_score = clamp((cosine_similarity(astro_a, astro_b) + 1.0) / 2.0) if include_astro and astro_a and astro_b else 0.0
    behavior_score = clamp(1.0 - mean_abs_diff(behavior_a, behavior_b)) if behavior_a and behavior_b else 0.5

    w_psy, w_astro, w_behavior = dynamic_weights(behavior_confidence, include_astro=include_astro)
    weighted_total = (w_psy * psycho_score) + (w_astro * astro_score) + (w_behavior * behavior_score)
    uncertainty_penalty = 0.0 if dynamics is None else dynamics.uncertainty_penalty
    final_score = clamp(weighted_total - uncertainty_penalty)

    confidence_weights = {"psycho": 0.45, "behavior": 0.25}
    confidence_values = {"psycho": clamp(psycho_confidence), "behavior": clamp(behavior_confidence)}
    if include_astro:
        confidence_weights["astro"] = 0.15
        confidence_values["astro"] = clamp(astro_confidence)
    if dynamics is not None:
        confidence_weights["dynamics"] = 0.15
        confidence_values["dynamics"] = clamp(dynamics.confidence)

    confidence_weight_total = sum(confidence_weights.values())
    confidence = clamp(sum(confidence_values[key] * confidence_weights[key] for key in confidence_values) / confidence_weight_total)
    if quality_flags.get("straight_lining"):
        confidence = clamp(confidence - 0.20)
    if quality_flags.get("speeding") or quality_flags.get("speeding_flag"):
        confidence = clamp(confidence - 0.10)
    if dynamics is not None:
        confidence = clamp(confidence - (dynamics.relational_risk_modifier * 0.30) - (dynamics.uncertainty_penalty * 0.20))

    explanation = _build_explanation(
        base_psycho_score=base_psycho_score,
        psycho_score=psycho_score,
        astro_score=astro_score,
        behavior_score=behavior_score,
        confidence=confidence,
        include_astro=include_astro,
        dynamics=dynamics,
    )

    return PairScore(
        psycho_score=psycho_score,
        astro_score=astro_score,
        behavior_score=behavior_score,
        final_score=final_score,
        confidence=confidence,
        explanation=explanation,
    )


def rank_pair_score(final_score: float, confidence: float) -> float:
    return clamp((final_score * 0.88) + (confidence * 0.12))


def explanation_highlights(explanation: dict[str, object], *, limit: int = 4) -> list[str]:
    items = []
    for driver in explanation.get("top_drivers", []) if isinstance(explanation, dict) else []:
        if isinstance(driver, dict) and driver.get("text"):
            items.append(str(driver["text"]))
    note = explanation.get("confidence_note") if isinstance(explanation, dict) else None
    if note:
        items.append(str(note))
    return items[:limit]


def explanation_reasons(explanation: dict[str, object], *, limit: int = 3) -> list[str]:
    reasons = explanation_highlights(explanation, limit=limit)
    return reasons[:limit] or ["This pairing may have some promising alignment, though the current insight remains directional."]


def explanation_watch_items(explanation: dict[str, object], *, limit: int = 2) -> list[str]:
    items = []
    for risk in explanation.get("risks", []) if isinstance(explanation, dict) else []:
        if isinstance(risk, dict) and risk.get("text"):
            items.append(str(risk["text"]))
    return items[:limit] or ["Treat the match read as guidance and keep checking fit through real communication."]


def _build_explanation(
    *,
    base_psycho_score: float,
    psycho_score: float,
    astro_score: float,
    behavior_score: float,
    confidence: float,
    include_astro: bool,
    dynamics: CompatibilityDynamicsResult | None,
) -> dict[str, object]:
    drivers: list[dict[str, object]] = []
    risks: list[dict[str, object]] = []

    if dynamics is not None:
        if dynamics.conflict_compatibility >= 0.6:
            drivers.append(
                {
                    "type": "psy",
                    "key": "conflict_repair_compatibility",
                    "impact": round(0.10 * dynamics.conflict_compatibility, 4),
                    "text": "You both seem to value direct emotional repair when tension shows up.",
                }
            )
        if dynamics.intimacy_pace_compatibility >= 0.58:
            drivers.append(
                {
                    "type": "psy",
                    "key": "intimacy_pace_compatibility",
                    "impact": round(0.09 * dynamics.intimacy_pace_compatibility, 4),
                    "text": "Your closeness pace may work well enough to help connection build without unnecessary pressure.",
                }
            )
        if dynamics.stability_exploration_compatibility >= 0.58:
            drivers.append(
                {
                    "type": "psy",
                    "key": "stability_exploration_alignment",
                    "impact": round(0.08 * dynamics.stability_exploration_compatibility, 4),
                    "text": "Your values around steadiness and novelty appear reasonably aligned.",
                }
            )
        if dynamics.attachment_compatibility >= 0.58:
            drivers.append(
                {
                    "type": "psy",
                    "key": "attachment_compatibility",
                    "impact": round(0.08 * dynamics.attachment_compatibility, 4),
                    "text": "The balance between closeness and independence may feel steadier in this pairing.",
                }
            )
        for text in dynamics.public_watch_items:
            risks.append(
                {
                    "type": "psy",
                    "key": "relational_watch_item",
                    "impact": round(float(-(dynamics.relational_risk_modifier + dynamics.uncertainty_penalty) / 2.0), 4),
                    "text": text,
                }
            )

    drivers.append(
        {
            "type": "psy",
            "key": "base_psych_overlap",
            "impact": round(0.07 * base_psycho_score, 4),
            "text": "There is some broader psychology overlap in how you may approach communication and relationship rhythm.",
        }
    )
    if include_astro:
        drivers.append(
            {
                "type": "astro",
                "key": "chart_harmony",
                "impact": round(0.06 * astro_score, 4),
                "text": "The astrology layer adds some extra resonance to the pairing.",
            }
        )
    drivers.append(
        {
            "type": "behavior",
            "key": "behavior_alignment",
            "impact": round(0.05 * behavior_score, 4),
            "text": "Your interaction pace may be easier to sustain when everyday responsiveness feels similar.",
        }
    )

    explanation = {
        "top_drivers": sorted(drivers, key=lambda driver: float(driver["impact"]), reverse=True)[:4],
        "risks": risks[:3],
        "confidence": round(confidence, 4),
        "confidence_note": (
            dynamics.confidence_note
            if dynamics is not None
            else "Current insight is still developing, so the match read stays intentionally tentative."
        ),
        "matching_preference": "psych_behavior_astro" if include_astro else "psych_behavior",
        "relational_dynamics": {
            "attachment": "steady" if dynamics and dynamics.attachment_compatibility >= 0.58 else "developing",
            "conflict": "repair_aligned" if dynamics and dynamics.conflict_compatibility >= 0.6 else "needs_patience",
            "intimacy_pace": "compatible" if dynamics and dynamics.intimacy_pace_compatibility >= 0.58 else "mixed",
            "affection": "recognizable" if dynamics and dynamics.affection_compatibility >= 0.58 else "mixed",
            "values": "aligned" if dynamics and dynamics.stability_exploration_compatibility >= 0.58 else "mixed",
        },
        "public_reasons": [] if dynamics is None else list(dynamics.public_reasons),
        "public_watch_items": [] if dynamics is None else list(dynamics.public_watch_items),
    }
    return explanation
