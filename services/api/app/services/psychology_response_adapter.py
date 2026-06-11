from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.models import PsychoItem, PsychoItemResponse, PsychoResponse
from app.psychology_item_bank import ITEM_BANK_BY_ID, PsychologyItemDefinition, get_item_definition


@dataclass(frozen=True)
class NormalizedPsychologyResponse:
    item_id: str
    answer_value: int | None
    first_answer_value: int | None
    final_answer_value: int | None
    considered_answer_value: int | None
    changed_answer_count: int
    response_time_ms: int | None
    returned_to_question: bool
    skipped: bool
    reverse_key: bool
    trait_key: str
    weight: float
    module: str
    dimension_group: str | None
    item_type: str
    version: str


def _coerce_item_definition(item: PsychoItem | PsychologyItemDefinition | None, item_id: str) -> tuple[bool, str, float, str, str | None, str, str]:
    if item is None:
        definition = get_item_definition(item_id)
        if definition is None:
            raise KeyError(f"missing_psychology_item_definition:{item_id}")
        item = definition

    return (
        bool(item.reverse_key),
        str(item.trait_key),
        float(item.weight),
        str(item.module),
        None if getattr(item, "dimension_group", None) is None else str(getattr(item, "dimension_group")),
        str(getattr(item, "item_type", "likert")),
        str(getattr(item, "version", "v1")),
    )


def adapt_legacy_psycho_responses(
    responses: Iterable[PsychoResponse],
    item_lookup: dict[str, PsychoItem | PsychologyItemDefinition] | None = None,
) -> dict[str, NormalizedPsychologyResponse]:
    item_lookup = item_lookup or ITEM_BANK_BY_ID
    normalized: dict[str, NormalizedPsychologyResponse] = {}

    for row in responses:
        reverse_key, trait_key, weight, module, dimension_group, item_type, version = _coerce_item_definition(
            item_lookup.get(row.item_id),
            row.item_id,
        )
        answer_value = int(row.answer)
        normalized[row.item_id] = NormalizedPsychologyResponse(
            item_id=row.item_id,
            answer_value=answer_value,
            first_answer_value=answer_value,
            final_answer_value=answer_value,
            considered_answer_value=answer_value,
            changed_answer_count=0,
            response_time_ms=None if row.response_ms is None else int(row.response_ms),
            returned_to_question=False,
            skipped=False,
            reverse_key=reverse_key,
            trait_key=trait_key,
            weight=weight,
            module=module,
            dimension_group=dimension_group,
            item_type=item_type,
            version=version,
        )

    return normalized


def adapt_assessment_item_responses(
    responses: Iterable[PsychoItemResponse],
    item_lookup: dict[str, PsychoItem | PsychologyItemDefinition] | None = None,
) -> dict[str, NormalizedPsychologyResponse]:
    item_lookup = item_lookup or ITEM_BANK_BY_ID
    normalized: dict[str, NormalizedPsychologyResponse] = {}

    for row in responses:
        reverse_key, trait_key, weight, module, dimension_group, item_type, version = _coerce_item_definition(
            item_lookup.get(row.item_id),
            row.item_id,
        )
        normalized[row.item_id] = NormalizedPsychologyResponse(
            item_id=row.item_id,
            answer_value=None if row.answer_value is None else int(row.answer_value),
            first_answer_value=None if row.first_answer_value is None else int(row.first_answer_value),
            final_answer_value=None if row.final_answer_value is None else int(row.final_answer_value),
            considered_answer_value=None if row.considered_answer_value is None else int(row.considered_answer_value),
            changed_answer_count=int(row.changed_answer_count or 0),
            response_time_ms=None if row.response_time_ms is None else int(row.response_time_ms),
            returned_to_question=bool(row.returned_to_question),
            skipped=bool(row.skipped),
            reverse_key=reverse_key,
            trait_key=trait_key,
            weight=weight,
            module=module,
            dimension_group=dimension_group,
            item_type=item_type,
            version=version,
        )

    return normalized


def build_normalized_response(
    *,
    item_id: str,
    answer_value: int | None = None,
    first_answer_value: int | None = None,
    final_answer_value: int | None = None,
    considered_answer_value: int | None = None,
    changed_answer_count: int = 0,
    response_time_ms: int | None = None,
    returned_to_question: bool = False,
    skipped: bool = False,
    reverse_key: bool | None = None,
    trait_key: str | None = None,
    weight: float | None = None,
    module: str | None = None,
    dimension_group: str | None = None,
    item_type: str | None = None,
    version: str | None = None,
) -> NormalizedPsychologyResponse:
    definition = get_item_definition(item_id)
    if definition is None:
        if None in (reverse_key, trait_key, weight, module):
            raise KeyError(f"missing_psychology_item_definition:{item_id}")
        resolved_reverse_key = bool(reverse_key)
        resolved_trait_key = str(trait_key)
        resolved_weight = float(weight)
        resolved_module = str(module)
        resolved_group = dimension_group
        resolved_type = "likert" if item_type is None else str(item_type)
        resolved_version = "v1" if version is None else str(version)
    else:
        resolved_reverse_key, resolved_trait_key, resolved_weight, resolved_module, resolved_group, resolved_type, resolved_version = _coerce_item_definition(
            definition,
            item_id,
        )
    return NormalizedPsychologyResponse(
        item_id=item_id,
        answer_value=answer_value,
        first_answer_value=first_answer_value,
        final_answer_value=final_answer_value,
        considered_answer_value=considered_answer_value,
        changed_answer_count=int(changed_answer_count),
        response_time_ms=response_time_ms,
        returned_to_question=returned_to_question,
        skipped=skipped,
        reverse_key=resolved_reverse_key if reverse_key is None else bool(reverse_key),
        trait_key=resolved_trait_key if trait_key is None else str(trait_key),
        weight=resolved_weight if weight is None else float(weight),
        module=resolved_module if module is None else str(module),
        dimension_group=resolved_group if dimension_group is None else dimension_group,
        item_type=resolved_type if item_type is None else str(item_type),
        version=resolved_version if version is None else str(version),
    )


# Canonical psych answer storage for the public assessment flow is now
# PsychoAssessmentSession + PsychoItemResponse.
# PsychoResponse remains as a compatibility layer for the legacy onboarding
# route and any surviving legacy readers while retirement is completed.
