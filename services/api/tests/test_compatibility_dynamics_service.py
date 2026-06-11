from types import SimpleNamespace

from app.services.compatibility_dynamics_service import (
    build_matching_psych_data,
    compute_compatibility_dynamics,
)


def _score(
    *,
    att_anxiety: float = 0.35,
    att_avoid: float = 0.3,
    conflict_direct: float = 0.7,
    conflict_avoid: float = 0.25,
    conflict_delay: float = 0.3,
    value_stability: float = 0.55,
    value_novelty: float = 0.45,
    aff_attention: float = 0.7,
    uncertainty: float = 0.18,
) -> SimpleNamespace:
    return SimpleNamespace(
        o=0.6,
        c=0.58,
        e=0.52,
        a=0.64,
        n=0.4,
        att_anxiety=att_anxiety,
        att_avoid=att_avoid,
        conflict_direct=conflict_direct,
        conflict_avoid=conflict_avoid,
        conflict_delay=conflict_delay,
        value_stability=value_stability,
        value_novelty=value_novelty,
        aff_attention=aff_attention,
        reassurance_need=0.55,
        independence_need=0.42,
        vulnerability_comfort=0.64,
        emotional_regulation=0.7,
        aff_touch=0.62,
        aff_words=0.68,
        aff_acts=0.57,
        aff_gifts=0.38,
        psycho_vector=[0.6, 0.58, 0.52, 0.64, 0.4, att_anxiety, att_avoid, conflict_direct, conflict_avoid, conflict_delay, value_stability, value_novelty, aff_attention, 0.5],
        psycho_uncertainty=[uncertainty] * 14,
        quality_flags={"canonical_dimension_version": "v2"},
    )


def _pattern(pattern_key: str, pattern_score: float, confidence: float = 0.75) -> SimpleNamespace:
    return SimpleNamespace(
        pattern_key=pattern_key,
        pattern_score=pattern_score,
        confidence=confidence,
    )


def _profile(
    *,
    love_language: str = "quality_time",
    communication_style: str = "direct",
    conflict_style: str = "collaborative",
    attachment_style: str = "secure",
    novelty_preference: float = 0.45,
    boundaries_preference: float = 0.4,
) -> SimpleNamespace:
    return SimpleNamespace(
        love_language=love_language,
        communication_style=communication_style,
        conflict_style=conflict_style,
        attachment_style=attachment_style,
        novelty_preference=novelty_preference,
        boundaries_preference=boundaries_preference,
        attachment_confidence=0.8,
    )


def test_compatibility_dynamics_is_deterministic_and_pattern_aware():
    a = build_matching_psych_data(
        psycho_score=_score(),
        derived_patterns=[
            _pattern("relational_security_profile", 0.72),
            _pattern("conflict_repair_style", 0.76),
            _pattern("intimacy_pace", 0.66),
            _pattern("stability_vs_exploration_profile", 0.48),
        ],
        psych_profile=_profile(),
        psych_confidence=0.82,
    )
    b = build_matching_psych_data(
        psycho_score=_score(att_anxiety=0.32, att_avoid=0.28, conflict_direct=0.74),
        derived_patterns=[
            _pattern("relational_security_profile", 0.74),
            _pattern("conflict_repair_style", 0.7),
            _pattern("intimacy_pace", 0.63),
            _pattern("stability_vs_exploration_profile", 0.51),
        ],
        psych_profile=_profile(),
        psych_confidence=0.78,
    )

    result_one = compute_compatibility_dynamics(a, b)
    result_two = compute_compatibility_dynamics(a, b)

    assert result_one == result_two
    assert result_one.overall_dynamics_score > 0.55
    assert result_one.conflict_compatibility > 0.55
    assert result_one.public_reasons
    assert "diagnosis" not in " ".join(result_one.public_reasons).lower()


def test_uncertainty_and_tension_reduce_dynamics_confidence_and_score():
    steady = build_matching_psych_data(
        psycho_score=_score(uncertainty=0.1),
        derived_patterns=[
            _pattern("relational_security_profile", 0.75, 0.8),
            _pattern("conflict_repair_style", 0.72, 0.8),
            _pattern("intimacy_pace", 0.65, 0.78),
            _pattern("emotional_reactivity_profile", 0.32, 0.8),
        ],
        psych_profile=_profile(),
        psych_confidence=0.84,
    )
    tense = build_matching_psych_data(
        psycho_score=_score(att_anxiety=0.8, att_avoid=0.72, conflict_direct=0.3, conflict_avoid=0.78, conflict_delay=0.74, uncertainty=0.5),
        derived_patterns=[
            _pattern("relational_security_profile", 0.28, 0.45),
            _pattern("conflict_repair_style", 0.25, 0.4),
            _pattern("intimacy_pace", 0.22, 0.4),
            _pattern("emotional_reactivity_profile", 0.82, 0.5),
        ],
        psych_profile=_profile(love_language="gifts", novelty_preference=0.8, boundaries_preference=0.75),
        psych_confidence=0.38,
    )

    result = compute_compatibility_dynamics(steady, tense)

    assert result.relational_risk_modifier > 0.08
    assert result.uncertainty_penalty > 0.1
    assert result.confidence < 0.6
    assert result.overall_dynamics_score < 0.5
    assert any("developing" in item.lower() or "patience" in item.lower() for item in result.public_watch_items + [result.confidence_note])


def test_canonical_dimensions_override_psych_profile_fallback_when_available():
    canonical = build_matching_psych_data(
        psycho_score=_score(),
        derived_patterns=[_pattern("relational_security_profile", 0.72)],
        psych_profile=_profile(love_language="gifts", novelty_preference=0.9, boundaries_preference=0.9),
        psych_confidence=0.8,
    )

    assert canonical is not None
    assert canonical.source == "canonical"
    assert canonical.traits["value_novelty"] == 0.45
    assert canonical.traits["independence_need"] == 0.42
    assert canonical.traits["aff_gifts"] == 0.38


def test_existing_psycho_score_no_longer_blends_psych_profile_fallback_values():
    partial_score = _score()
    partial_score.quality_flags = {}

    data = build_matching_psych_data(
        psycho_score=partial_score,
        derived_patterns=[_pattern("relational_security_profile", 0.72)],
        psych_profile=_profile(love_language="gifts", novelty_preference=0.9, boundaries_preference=0.9),
        psych_confidence=0.8,
    )

    assert data is not None
    assert data.source == "canonical_partial"
    assert data.traits["value_novelty"] == 0.45
    assert data.traits["independence_need"] == 0.42
    assert data.traits["aff_attention"] == 0.7
