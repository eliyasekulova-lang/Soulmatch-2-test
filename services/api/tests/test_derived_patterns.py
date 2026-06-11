from app.services.derived_patterns_service import derive_patterns


def test_derived_patterns_returns_expected_internal_constructs():
    traits = {
        "N": 0.75,
        "att_anxiety": 0.7,
        "emotional_regulation": 0.25,
        "att_avoid": 0.2,
        "vulnerability_comfort": 0.7,
        "conflict_direct": 0.65,
        "conflict_avoid": 0.3,
        "A": 0.8,
        "independence_need": 0.55,
        "conflict_delay": 0.4,
        "O": 0.7,
        "value_novelty": 0.8,
        "value_stability": 0.35,
    }
    uncertainties = {key: 0.2 for key in traits}

    patterns = derive_patterns(traits, uncertainties, confidence_modifier=0.9)
    pattern_map = {pattern.pattern_key: pattern for pattern in patterns}

    assert set(pattern_map) == {
        "emotional_reactivity_profile",
        "relational_security_profile",
        "conflict_repair_style",
        "intimacy_pace",
        "stability_vs_exploration_profile",
    }
    assert pattern_map["emotional_reactivity_profile"].pattern_score > 0.6
    assert pattern_map["relational_security_profile"].confidence > 0.5
    assert "diagnosis" not in pattern_map["emotional_reactivity_profile"].explanation_internal.lower()
