from app.services.psychology_response_adapter import build_normalized_response
from app.services.psychology_scoring_service import PSYCH_VECTOR_ORDER, score_psychology_responses


def test_psychology_scoring_is_deterministic_and_normalized():
    responses = {
        "B5_O_01": build_normalized_response(item_id="B5_O_01", answer_value=5),
        "B5_O_02": build_normalized_response(item_id="B5_O_02", answer_value=1),
        "B5_O_03": build_normalized_response(item_id="B5_O_03", answer_value=5),
        "B5_O_04": build_normalized_response(item_id="B5_O_04", answer_value=1),
        "B5_O_05": build_normalized_response(item_id="B5_O_05", answer_value=4),
        "ATT_01": build_normalized_response(item_id="ATT_01", answer_value=4, response_time_ms=1800),
        "ATT_03": build_normalized_response(item_id="ATT_03", answer_value=2, response_time_ms=1700),
        "CON_01": build_normalized_response(item_id="CON_01", answer_value=4, response_time_ms=2000),
        "CON_03": build_normalized_response(item_id="CON_03", answer_value=2, response_time_ms=2100),
        "REG_01": build_normalized_response(item_id="REG_01", answer_value=4, response_time_ms=2200),
    }

    first = score_psychology_responses(responses)
    second = score_psychology_responses(responses)

    assert first == second
    assert len(first.vector) == len(PSYCH_VECTOR_ORDER)
    assert all(0.0 <= value <= 1.0 for value in first.vector)
    assert all(0.0 <= value <= 1.0 for value in first.uncertainty)


def test_psychology_scoring_handles_reverse_keys_and_sparse_uncertainty():
    responses = {
        "B5_C_02": build_normalized_response(item_id="B5_C_02", answer_value=1),
        "B5_C_04": build_normalized_response(item_id="B5_C_04", answer_value=1),
        "AFF_01": build_normalized_response(item_id="AFF_01", answer_value=5, response_time_ms=250),
    }

    result = score_psychology_responses(responses)

    assert result.traits["C"] > 0.75
    assert result.uncertainty[PSYCH_VECTOR_ORDER.index("C")] > 0.2
    assert result.quality_flags["speeding"] is False
    assert result.dimension_counts["C"] == 2


def test_psychology_scoring_quality_flags_capture_speeding_and_tension():
    responses = {}
    for item_id in ("B5_O_01", "B5_O_02", "B5_O_03", "B5_O_04", "B5_O_05", "VAL_01", "VAL_03", "VAL_05"):
        responses[item_id] = build_normalized_response(item_id=item_id, answer_value=5, response_time_ms=200)
    for item_id in ("ATT_05", "ATT_09", "ATT_14", "CON_03", "REG_02"):
        responses[item_id] = build_normalized_response(
            item_id=item_id,
            answer_value=5,
            first_answer_value=2,
            final_answer_value=5,
            considered_answer_value=5,
            changed_answer_count=2,
            returned_to_question=True,
            response_time_ms=240,
        )

    result = score_psychology_responses(responses)

    assert result.quality_flags["speeding"] is True
    assert result.quality_flags["contradiction_score"] > 0
    assert "closeness_and_independence_pull" in result.quality_flags["meaningful_tensions"]
