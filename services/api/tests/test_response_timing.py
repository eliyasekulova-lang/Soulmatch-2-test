from app.services.psychology_response_adapter import build_normalized_response
from app.services.response_timing_service import analyze_response_timing


def test_response_timing_interprets_reflection_without_penalizing_it():
    responses = [
        build_normalized_response(item_id="B5_O_01", answer_value=4, response_time_ms=2800),
        build_normalized_response(
            item_id="ATT_05",
            answer_value=4,
            first_answer_value=3,
            final_answer_value=4,
            considered_answer_value=4,
            changed_answer_count=1,
            returned_to_question=True,
            response_time_ms=3100,
        ),
        build_normalized_response(item_id="REG_01", answer_value=4, response_time_ms=2600),
    ]

    summary = analyze_response_timing(responses)

    assert summary.speeding_flag is False
    assert summary.reflection_score > 0.4
    assert summary.timing_confidence > 0.5


def test_response_timing_flags_speeding_and_ambivalence_signals():
    responses = [
        build_normalized_response(
            item_id="B5_O_01",
            answer_value=5,
            first_answer_value=2,
            final_answer_value=5,
            considered_answer_value=5,
            changed_answer_count=2,
            returned_to_question=True,
            response_time_ms=220,
        )
        for _ in range(8)
    ]

    summary = analyze_response_timing(responses)

    assert summary.speeding_flag is True
    assert summary.ambivalence_score > 0.3
    assert summary.change_signal > 0.3
    assert summary.return_signal > 0.9
