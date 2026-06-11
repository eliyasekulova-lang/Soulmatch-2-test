from __future__ import annotations

from dataclasses import dataclass

from app.models import PsychProfile, PsychoDerivedPattern, PsychoScore

from .derived_patterns_service import clamp


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

MATCHING_TRAIT_KEYS = [
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
class MatchingPsychData:
    source: str
    traits: dict[str, float]
    vector: list[float]
    uncertainty: list[float]
    pattern_scores: dict[str, float]
    pattern_confidences: dict[str, float]
    quality_flags: dict[str, object]
    psych_confidence: float
    love_language: str | None
    communication_style: str | None
    conflict_style: str | None
    attachment_style: str | None
    novelty_preference: float | None
    boundaries_preference: float | None


@dataclass(frozen=True)
class CompatibilityDynamicsResult:
    attachment_compatibility: float
    conflict_compatibility: float
    intimacy_pace_compatibility: float
    affection_compatibility: float
    stability_exploration_compatibility: float
    relational_risk_modifier: float
    uncertainty_penalty: float
    overall_dynamics_score: float
    confidence: float
    public_reasons: list[str]
    public_watch_items: list[str]
    confidence_note: str
    internal_explanation_artifacts: dict[str, object]


def build_matching_psych_data(
    *,
    psycho_score: PsychoScore | None,
    derived_patterns: list[PsychoDerivedPattern] | None = None,
    psych_profile: PsychProfile | None = None,
    psych_confidence: float | None = None,
) -> MatchingPsychData | None:
    # Canonical matching input is the session-derived PsychoScore plus persisted
    # PsychoDerivedPattern rows. PsychProfile is now only a residual fallback
    # for users who do not yet have any persisted PsychoScore row.
    derived_patterns = list(derived_patterns or [])
    if psycho_score is None and psych_profile is None:
        return None

    traits = _traits_from_sources(psycho_score=psycho_score, psych_profile=psych_profile)
    vector = list(psycho_score.psycho_vector or []) if psycho_score else _vector_from_traits(traits)
    uncertainty = list(psycho_score.psycho_uncertainty or []) if psycho_score else [0.45] * len(PSY_ORDER)
    pattern_scores = {pattern.pattern_key: float(pattern.pattern_score) for pattern in derived_patterns}
    pattern_confidences = {pattern.pattern_key: float(pattern.confidence) for pattern in derived_patterns}

    resolved_confidence = psych_confidence
    if resolved_confidence is None:
        if psycho_score and vector:
            resolved_confidence = clamp(1.0 - (sum(uncertainty) / float(len(uncertainty) or 1)))
        elif psych_profile:
            resolved_confidence = float(psych_profile.attachment_confidence or 0.55)
        else:
            resolved_confidence = 0.5

    return MatchingPsychData(
        source="canonical" if psycho_score and _has_canonical_expanded_dims(psycho_score) else ("canonical_partial" if psycho_score else "psych_profile_fallback"),
        traits=traits,
        vector=vector,
        uncertainty=uncertainty,
        pattern_scores=pattern_scores,
        pattern_confidences=pattern_confidences,
        quality_flags={} if psycho_score is None else dict(psycho_score.quality_flags or {}),
        psych_confidence=clamp(float(resolved_confidence)),
        love_language=None if psych_profile is None else psych_profile.love_language,
        communication_style=None if psych_profile is None else psych_profile.communication_style,
        conflict_style=None if psych_profile is None else psych_profile.conflict_style,
        attachment_style=None if psych_profile is None else psych_profile.attachment_style,
        novelty_preference=None if psych_profile is None else float(psych_profile.novelty_preference),
        boundaries_preference=None if psych_profile is None else float(psych_profile.boundaries_preference),
    )


def compute_compatibility_dynamics(
    source: MatchingPsychData | None,
    target: MatchingPsychData | None,
) -> CompatibilityDynamicsResult:
    if source is None or target is None:
        return CompatibilityDynamicsResult(
            attachment_compatibility=0.5,
            conflict_compatibility=0.5,
            intimacy_pace_compatibility=0.5,
            affection_compatibility=0.5,
            stability_exploration_compatibility=0.5,
            relational_risk_modifier=0.0,
            uncertainty_penalty=0.12,
            overall_dynamics_score=0.44,
            confidence=0.35,
            public_reasons=["Current psychology insight is still developing, so this read stays fairly tentative."],
            public_watch_items=["Use early conversations to compare pace, conflict style, and everyday expectations."],
            confidence_note="Current insight is still developing, so the relational read is intentionally cautious.",
            internal_explanation_artifacts={"source": "insufficient_psych_data"},
        )

    attachment = _attachment_compatibility(source, target)
    conflict = _conflict_compatibility(source, target)
    intimacy = _intimacy_compatibility(source, target)
    affection = _affection_compatibility(source, target)
    stability = _stability_compatibility(source, target)
    uncertainty_penalty = _uncertainty_penalty(source, target)
    relational_risk_modifier = _relational_risk_modifier(source, target, attachment=attachment, conflict=conflict, intimacy=intimacy)
    pattern_confidences = list(source.pattern_confidences.values()) + list(target.pattern_confidences.values())
    pattern_confidence = sum(pattern_confidences) / float(len(pattern_confidences) or 1) if pattern_confidences else 0.55
    confidence_penalty = clamp(
        (1.0 - ((source.psych_confidence + target.psych_confidence + pattern_confidence) / 3.0)) * 0.14,
        0.0,
        0.06,
    )

    base = (
        (attachment * 0.24)
        + (conflict * 0.24)
        + (intimacy * 0.18)
        + (affection * 0.14)
        + (stability * 0.20)
    )
    overall = clamp(base - relational_risk_modifier - uncertainty_penalty - confidence_penalty)

    confidence = clamp(
        (source.psych_confidence * 0.32)
        + (target.psych_confidence * 0.32)
        + (pattern_confidence * 0.20)
        + ((1.0 - uncertainty_penalty) * 0.08)
        - (uncertainty_penalty * 0.22)
        - (relational_risk_modifier * 0.18)
    )

    public_reasons = _build_public_reasons(
        attachment=attachment,
        conflict=conflict,
        intimacy=intimacy,
        affection=affection,
        stability=stability,
    )
    public_watch_items = _build_public_watch_items(
        attachment=attachment,
        conflict=conflict,
        intimacy=intimacy,
        relational_risk_modifier=relational_risk_modifier,
        uncertainty_penalty=uncertainty_penalty,
    )
    confidence_note = _confidence_note(confidence)

    return CompatibilityDynamicsResult(
        attachment_compatibility=attachment,
        conflict_compatibility=conflict,
        intimacy_pace_compatibility=intimacy,
        affection_compatibility=affection,
        stability_exploration_compatibility=stability,
        relational_risk_modifier=relational_risk_modifier,
        uncertainty_penalty=uncertainty_penalty,
        overall_dynamics_score=overall,
        confidence=confidence,
        public_reasons=public_reasons,
        public_watch_items=public_watch_items,
        confidence_note=confidence_note,
        internal_explanation_artifacts={
            "source_a": source.source,
            "source_b": target.source,
            "pattern_confidence": round(pattern_confidence, 4),
            "confidence_penalty": round(confidence_penalty, 4),
            "subscores": {
                "attachment": round(attachment, 4),
                "conflict": round(conflict, 4),
                "intimacy": round(intimacy, 4),
                "affection": round(affection, 4),
                "stability": round(stability, 4),
            },
        },
    )


def _traits_from_sources(*, psycho_score: PsychoScore | None, psych_profile: PsychProfile | None) -> dict[str, float]:
    traits = {key: 0.5 for key in MATCHING_TRAIT_KEYS}
    if psycho_score is not None:
        traits.update(
            {
                "O": float(psycho_score.o),
                "C": float(psycho_score.c),
                "E": float(psycho_score.e),
                "A": float(psycho_score.a),
                "N": float(psycho_score.n),
                "att_anxiety": float(psycho_score.att_anxiety),
                "att_avoid": float(psycho_score.att_avoid),
                "reassurance_need": float(psycho_score.reassurance_need),
                "independence_need": float(psycho_score.independence_need),
                "vulnerability_comfort": float(psycho_score.vulnerability_comfort),
                "conflict_direct": float(psycho_score.conflict_direct),
                "conflict_avoid": float(psycho_score.conflict_avoid),
                "conflict_delay": float(psycho_score.conflict_delay),
                "emotional_regulation": float(psycho_score.emotional_regulation),
                "value_stability": float(psycho_score.value_stability),
                "value_novelty": float(psycho_score.value_novelty),
                "aff_attention": float(psycho_score.aff_attention),
                "aff_touch": float(psycho_score.aff_touch),
                "aff_words": float(psycho_score.aff_words),
                "aff_acts": float(psycho_score.aff_acts),
                "aff_gifts": float(psycho_score.aff_gifts),
            }
        )
    if psycho_score is None and psych_profile is not None:
        traits["value_novelty"] = float(psych_profile.novelty_preference)
        traits["value_stability"] = clamp(1.0 - float(psych_profile.novelty_preference))
        traits["att_avoid"] = clamp((traits.get("att_avoid", 0.5) * 0.7) + (float(psych_profile.boundaries_preference) * 0.3))
        traits["aff_attention"] = max(traits.get("aff_attention", 0.5), _love_language_attention_bias(psych_profile.love_language))
        traits["independence_need"] = max(traits.get("independence_need", 0.5), float(psych_profile.boundaries_preference))
        traits.update(_love_language_trait_biases(psych_profile.love_language))
    return traits


def _vector_from_traits(traits: dict[str, float]) -> list[float]:
    return [float(traits.get(key, 0.5)) for key in PSY_ORDER]


def _pattern_score(data: MatchingPsychData, key: str, default: float) -> float:
    return float(data.pattern_scores.get(key, default))


def _pattern_confidence(data: MatchingPsychData, key: str, default: float = 0.55) -> float:
    return float(data.pattern_confidences.get(key, default))


def _attachment_compatibility(a: MatchingPsychData, b: MatchingPsychData) -> float:
    security_alignment = 1.0 - abs(
        _pattern_score(a, "relational_security_profile", 0.5) - _pattern_score(b, "relational_security_profile", 0.5)
    )
    anxiety_balance = 1.0 - clamp(abs(a.traits["att_anxiety"] - b.traits["att_anxiety"]) * 0.85)
    avoidance_balance = 1.0 - clamp(abs(a.traits["att_avoid"] - b.traits["att_avoid"]) * 0.85)
    reassurance_gap = abs(a.traits["reassurance_need"] - b.traits["reassurance_need"])
    vulnerability_gap = abs(a.traits["vulnerability_comfort"] - b.traits["vulnerability_comfort"])
    pursuit_with_distance_penalty = 0.12 if (
        max(a.traits["att_anxiety"], b.traits["att_anxiety"]) > 0.7
        and max(a.traits["att_avoid"], b.traits["att_avoid"]) > 0.7
    ) else 0.0
    return clamp(
        (security_alignment * 0.28)
        + (anxiety_balance * 0.20)
        + (avoidance_balance * 0.20)
        + ((1.0 - reassurance_gap) * 0.16)
        + ((1.0 - vulnerability_gap) * 0.16)
        - pursuit_with_distance_penalty
    )


def _conflict_compatibility(a: MatchingPsychData, b: MatchingPsychData) -> float:
    direct_gap = abs(a.traits["conflict_direct"] - b.traits["conflict_direct"])
    avoid_gap = abs(a.traits["conflict_avoid"] - b.traits["conflict_avoid"])
    delay_gap = abs(a.traits["conflict_delay"] - b.traits["conflict_delay"])
    repair_gap = abs(_pattern_score(a, "conflict_repair_style", 0.5) - _pattern_score(b, "conflict_repair_style", 0.5))
    regulation_gap = abs(a.traits["emotional_regulation"] - b.traits["emotional_regulation"])
    mixed_speed_penalty = 0.10 if delay_gap > 0.45 and min(a.traits["conflict_direct"], b.traits["conflict_direct"]) < 0.45 else 0.0
    return clamp(
        (1.0 - direct_gap) * 0.24
        + (1.0 - avoid_gap) * 0.20
        + (1.0 - delay_gap) * 0.18
        + (1.0 - repair_gap) * 0.20
        + (1.0 - regulation_gap) * 0.18
        - mixed_speed_penalty
    )


def _intimacy_compatibility(a: MatchingPsychData, b: MatchingPsychData) -> float:
    pace_gap = abs(_pattern_score(a, "intimacy_pace", 0.5) - _pattern_score(b, "intimacy_pace", 0.5))
    closeness_gap = abs((1.0 - a.traits["att_avoid"]) - (1.0 - b.traits["att_avoid"]))
    delay_gap = abs(a.traits["conflict_delay"] - b.traits["conflict_delay"])
    independence_gap = abs(a.traits["independence_need"] - b.traits["independence_need"])
    return clamp((1.0 - pace_gap) * 0.35 + (1.0 - closeness_gap) * 0.25 + (1.0 - delay_gap) * 0.15 + (1.0 - independence_gap) * 0.25)


def _affection_compatibility(a: MatchingPsychData, b: MatchingPsychData) -> float:
    gaps = [
        abs(a.traits["aff_attention"] - b.traits["aff_attention"]),
        abs(a.traits["aff_touch"] - b.traits["aff_touch"]),
        abs(a.traits["aff_words"] - b.traits["aff_words"]),
        abs(a.traits["aff_acts"] - b.traits["aff_acts"]),
        abs(a.traits["aff_gifts"] - b.traits["aff_gifts"]),
    ]
    language_alignment = 1.0 if a.love_language and b.love_language and a.love_language == b.love_language else 0.7
    return clamp(((1.0 - (sum(gaps) / float(len(gaps)))) * 0.85) + (language_alignment * 0.15))


def _stability_compatibility(a: MatchingPsychData, b: MatchingPsychData) -> float:
    pattern_gap = abs(
        _pattern_score(a, "stability_vs_exploration_profile", a.traits["value_novelty"])
        - _pattern_score(b, "stability_vs_exploration_profile", b.traits["value_novelty"])
    )
    values_gap = (
        abs(a.traits["value_stability"] - b.traits["value_stability"])
        + abs(a.traits["value_novelty"] - b.traits["value_novelty"])
    ) / 2.0
    return clamp((1.0 - pattern_gap) * 0.55 + (1.0 - values_gap) * 0.45)


def _relational_risk_modifier(
    a: MatchingPsychData,
    b: MatchingPsychData,
    *,
    attachment: float,
    conflict: float,
    intimacy: float,
) -> float:
    reactivity_pull = max(_pattern_score(a, "emotional_reactivity_profile", 0.5), _pattern_score(b, "emotional_reactivity_profile", 0.5))
    low_repair = 1.0 - min(_pattern_score(a, "conflict_repair_style", 0.5), _pattern_score(b, "conflict_repair_style", 0.5))
    low_regulation = 1.0 - min(a.traits["emotional_regulation"], b.traits["emotional_regulation"])
    quality_penalty = 0.0
    for flags in (a.quality_flags, b.quality_flags):
        if flags.get("straight_lining"):
            quality_penalty += 0.05
        if flags.get("speeding") or flags.get("speeding_flag"):
            quality_penalty += 0.03
        if int(flags.get("inconsistent_pairs", 0) or 0) > 0:
            quality_penalty += 0.03

    tension_penalty = 0.0
    if attachment < 0.48:
        tension_penalty += 0.05
    if conflict < 0.46 and reactivity_pull > 0.58:
        tension_penalty += 0.06
    if intimacy < 0.48 and max(a.traits["att_anxiety"], b.traits["att_anxiety"]) > 0.62:
        tension_penalty += 0.04
    return clamp((reactivity_pull * 0.05) + (low_repair * 0.05) + (low_regulation * 0.04) + quality_penalty + tension_penalty, 0.0, 0.3)


def _uncertainty_penalty(a: MatchingPsychData, b: MatchingPsychData) -> float:
    avg_uncertainty = (
        (sum(a.uncertainty) / float(len(a.uncertainty) or 1))
        + (sum(b.uncertainty) / float(len(b.uncertainty) or 1))
    ) / 2.0
    pattern_confidence = (
        sum(list(a.pattern_confidences.values()) + list(b.pattern_confidences.values()))
        / float(len(a.pattern_confidences) + len(b.pattern_confidences) or 1)
    ) if (a.pattern_confidences or b.pattern_confidences) else 0.55
    return clamp((avg_uncertainty * 0.20) + ((1.0 - pattern_confidence) * 0.12), 0.0, 0.28)


def _build_public_reasons(
    *,
    attachment: float,
    conflict: float,
    intimacy: float,
    affection: float,
    stability: float,
) -> list[str]:
    reasons: list[str] = []
    if conflict >= 0.62:
        reasons.append("You both may work well when it comes to direct emotional repair after tension.")
    if intimacy >= 0.60:
        reasons.append("Your closeness pace appears reasonably compatible, which may help connection build more naturally.")
    if stability >= 0.60:
        reasons.append("Your values around stability and novelty appear aligned enough to support a shared rhythm.")
    if affection >= 0.60:
        reasons.append("You may show care in ways that feel mutually recognizable rather than mismatched.")
    if attachment >= 0.58:
        reasons.append("Your relational signals suggest a steadier balance between closeness and independence.")
    return reasons[:3] or ["This pairing shows some relational alignment across communication, pace, and shared expectations."]


def _build_public_watch_items(
    *,
    attachment: float,
    conflict: float,
    intimacy: float,
    relational_risk_modifier: float,
    uncertainty_penalty: float,
) -> list[str]:
    watch_items: list[str] = []
    if intimacy < 0.5:
        watch_items.append("This match may require patience because one of you may warm into closeness faster than the other.")
    if conflict < 0.5:
        watch_items.append("You may need clearer check-ins around how quickly each person likes to revisit tension.")
    if attachment < 0.5:
        watch_items.append("It may help to name reassurance and space needs early so neither person has to guess.")
    if uncertainty_penalty > 0.10 or relational_risk_modifier > 0.12:
        watch_items.append("Current insight is still developing, so real-world communication should carry more weight than the initial read.")
    return watch_items[:2] or ["Treat this compatibility read as a starting point and keep adjusting through real conversation."]


def _confidence_note(confidence: float) -> str:
    if confidence >= 0.72:
        return "The current psychology read is fairly steady, so these relational insights may be directionally useful."
    if confidence >= 0.5:
        return "The current psychology read has moderate confidence, so these insights are best used as guidance rather than certainty."
    return "Current insight is still developing, so the explanation stays intentionally tentative."


def _love_language_attention_bias(love_language: str | None) -> float:
    if love_language in {"quality_time", "words_of_affirmation"}:
        return 0.72
    if love_language in {"acts_of_service", "physical_touch"}:
        return 0.55
    if love_language == "gifts":
        return 0.42
    return 0.5


def _love_language_trait_biases(love_language: str | None) -> dict[str, float]:
    if love_language == "quality_time":
        return {"aff_attention": 0.75}
    if love_language == "physical_touch":
        return {"aff_touch": 0.75}
    if love_language == "words_of_affirmation":
        return {"aff_words": 0.75}
    if love_language == "acts_of_service":
        return {"aff_acts": 0.75}
    if love_language == "gifts":
        return {"aff_gifts": 0.75}
    return {}


def _has_canonical_expanded_dims(psycho_score: PsychoScore | None) -> bool:
    if psycho_score is None:
        return False
    quality_flags = dict(psycho_score.quality_flags or {})
    return quality_flags.get("canonical_dimension_version") == "v2"
