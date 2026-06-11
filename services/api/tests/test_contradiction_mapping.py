from app.services.contradiction_mapping_service import evaluate_contradictions
from app.services.psychology_response_adapter import build_normalized_response


def test_contradiction_mapping_separates_quality_concerns_from_meaningful_tensions():
    traits = {
        "reassurance_need": 0.8,
        "independence_need": 0.75,
        "vulnerability_comfort": 0.7,
        "att_anxiety": 0.72,
        "conflict_avoid": 0.8,
        "emotional_regulation": 0.25,
        "O": 0.8,
        "value_stability": 0.78,
        "A": 0.8,
        "conflict_direct": 0.2,
    }
    responses = {
        "B5_O_01": build_normalized_response(item_id="B5_O_01", answer_value=5),
        "B5_O_02": build_normalized_response(item_id="B5_O_02", answer_value=5),
        "ATT_01": build_normalized_response(item_id="ATT_01", answer_value=5),
        "ATT_08": build_normalized_response(item_id="ATT_08", answer_value=5),
    }

    result = evaluate_contradictions(traits, responses)

    assert "openness_inconsistency" in result.quality_concerns
    assert "closeness_and_independence_pull" in result.meaningful_tensions
    assert "trust_and_abandonment_tension" in result.meaningful_tensions
    assert result.contradiction_score > 0
    assert result.confidence_modifier < 1.0
