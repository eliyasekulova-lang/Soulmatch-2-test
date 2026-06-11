from datetime import datetime

from app.models import PsychoItemResponse, PsychoResponse
from app.services.psychology_response_adapter import (
    adapt_assessment_item_responses,
    adapt_legacy_psycho_responses,
)


def test_legacy_psycho_response_adapter_normalizes_current_runtime_shape():
    row = PsychoResponse(
        user_id="user-1",
        item_id="B5_O_01",
        answer=4,
        response_ms=1800,
        created_at=datetime.utcnow(),
    )

    adapted = adapt_legacy_psycho_responses([row])

    assert adapted["B5_O_01"].answer_value == 4
    assert adapted["B5_O_01"].considered_answer_value == 4
    assert adapted["B5_O_01"].changed_answer_count == 0
    assert adapted["B5_O_01"].trait_key == "O"


def test_new_psycho_item_response_adapter_normalizes_future_ready_shape():
    row = PsychoItemResponse(
        user_id="user-1",
        session_id="session-1",
        item_id="ATT_05",
        answer_value=4,
        first_answer_value=2,
        final_answer_value=4,
        considered_answer_value=4,
        changed_answer_count=2,
        response_time_ms=2100,
        returned_to_question=True,
        skipped=False,
        created_at=datetime.utcnow(),
    )

    adapted = adapt_assessment_item_responses([row])

    assert adapted["ATT_05"].first_answer_value == 2
    assert adapted["ATT_05"].returned_to_question is True
    assert adapted["ATT_05"].trait_key == "reassurance_need"
    assert adapted["ATT_05"].module == "attachment"
