from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PsychologyItemDefinition:
    id: str
    module: str
    prompt: str
    reverse_key: bool
    trait_key: str
    weight: float
    item_type: str
    version: str
    dimension_group: str
    is_active: bool
    followup_eligible: bool


def _item(
    item_id: str,
    module: str,
    prompt: str,
    reverse_key: bool,
    trait_key: str,
    dimension_group: str,
    *,
    weight: float = 1.0,
    version: str = "v2",
    item_type: str = "likert",
    followup_eligible: bool = False,
) -> PsychologyItemDefinition:
    return PsychologyItemDefinition(
        id=item_id,
        module=module,
        prompt=prompt,
        reverse_key=reverse_key,
        trait_key=trait_key,
        weight=weight,
        item_type=item_type,
        version=version,
        dimension_group=dimension_group,
        is_active=True,
        followup_eligible=followup_eligible,
    )


STANDARD_ITEM_BANK: tuple[PsychologyItemDefinition, ...] = (
    _item("B5_O_01", "big5", "I enjoy exploring new ideas and concepts.", False, "O", "openness", version="v1"),
    _item("B5_O_02", "big5", "I prefer familiar routines over new experiences.", True, "O", "openness", version="v1"),
    _item("B5_O_03", "big5", "I am curious about abstract or philosophical topics.", False, "O", "openness", version="v1"),
    _item("B5_O_04", "big5", "I avoid complex or unusual ideas.", True, "O", "openness", version="v1"),
    _item("B5_O_05", "big5", "I like experimenting with new ways of doing things.", False, "O", "openness"),
    _item("B5_C_01", "big5", "I complete tasks efficiently and reliably.", False, "C", "conscientiousness", version="v1"),
    _item("B5_C_02", "big5", "I tend to procrastinate.", True, "C", "conscientiousness", version="v1"),
    _item("B5_C_03", "big5", "I keep my environment organized.", False, "C", "conscientiousness", version="v1"),
    _item("B5_C_04", "big5", "I often act without planning.", True, "C", "conscientiousness", version="v1"),
    _item("B5_C_05", "big5", "I usually follow through on commitments I make.", False, "C", "conscientiousness"),
    _item("B5_E_01", "big5", "I feel energized when interacting with people.", False, "E", "extraversion", version="v1"),
    _item("B5_E_02", "big5", "I prefer spending most of my time alone.", True, "E", "extraversion", version="v1"),
    _item("B5_E_03", "big5", "I am comfortable being the center of attention.", False, "E", "extraversion", version="v1"),
    _item("B5_E_04", "big5", "I avoid social situations.", True, "E", "extraversion", version="v1"),
    _item("B5_E_05", "big5", "I start conversations easily in new settings.", False, "E", "extraversion"),
    _item("B5_A_01", "big5", "I am considerate of others' feelings.", False, "A", "agreeableness", version="v1"),
    _item("B5_A_02", "big5", "I can be cold or distant.", True, "A", "agreeableness", version="v1"),
    _item("B5_A_03", "big5", "I try to cooperate rather than compete.", False, "A", "agreeableness", version="v1"),
    _item("B5_A_04", "big5", "I get irritated by others easily.", True, "A", "agreeableness", version="v1"),
    _item("B5_A_05", "big5", "I usually look for common ground during disagreements.", False, "A", "agreeableness"),
    _item("B5_N_01", "big5", "I worry about things frequently.", False, "N", "neuroticism", version="v1"),
    _item("B5_N_02", "big5", "I remain calm under stress.", True, "N", "neuroticism", version="v1"),
    _item("B5_N_03", "big5", "My mood changes easily.", False, "N", "neuroticism", version="v1"),
    _item("B5_N_04", "big5", "I feel emotionally stable most of the time.", True, "N", "neuroticism", version="v1"),
    _item("B5_N_05", "big5", "Small setbacks can stay with me for a while.", False, "N", "neuroticism"),
    _item("ATT_01", "attachment", "I worry that people I care about may lose interest in me.", False, "att_anxiety", "attachment", version="v1", followup_eligible=True),
    _item("ATT_02", "attachment", "I prefer maintaining emotional independence in relationships.", False, "att_avoid", "attachment", version="v1", followup_eligible=True),
    _item("ATT_03", "attachment", "I find it easy to trust others deeply.", True, "att_anxiety", "attachment", version="v1"),
    _item("ATT_04", "attachment", "I become uncomfortable when people get too close emotionally.", False, "att_avoid", "attachment", version="v1", followup_eligible=True),
    _item("ATT_05", "attachment", "I need reassurance when a relationship feels uncertain.", False, "reassurance_need", "attachment", followup_eligible=True),
    _item("ATT_06", "attachment", "I am comfortable relying on someone I trust.", False, "vulnerability_comfort", "attachment"),
    _item("ATT_07", "attachment", "I keep a lot of emotional distance even when I care about someone.", False, "att_avoid", "attachment", followup_eligible=True),
    _item("ATT_08", "attachment", "I can stay grounded even if I do not hear back right away.", True, "att_anxiety", "attachment"),
    _item("ATT_09", "attachment", "I like having a strong sense of personal space in close relationships.", False, "independence_need", "attachment"),
    _item("ATT_10", "attachment", "I can share vulnerable thoughts without feeling exposed for too long.", False, "vulnerability_comfort", "attachment"),
    _item("ATT_11", "attachment", "Silence from someone important can make me question where I stand.", False, "att_anxiety", "attachment", followup_eligible=True),
    _item("ATT_12", "attachment", "Too much emotional closeness can feel draining for me.", False, "att_avoid", "attachment", followup_eligible=True),
    _item("ATT_13", "attachment", "I generally do not need much reassurance to feel secure with someone.", True, "reassurance_need", "attachment"),
    _item("ATT_14", "attachment", "I like preserving independence even in committed relationships.", False, "independence_need", "attachment"),
    _item("ATT_15", "attachment", "Opening up emotionally usually feels relieving rather than risky.", False, "vulnerability_comfort", "attachment"),
    _item("CON_01", "conflict", "When conflict happens, I prefer to resolve it immediately.", False, "conflict_direct", "conflict", version="v1"),
    _item("CON_02", "conflict", "I need time alone before discussing emotional conflict.", False, "conflict_delay", "conflict", version="v1"),
    _item("CON_03", "conflict", "I avoid conflict even when something bothers me.", False, "conflict_avoid", "conflict", version="v1"),
    _item("CON_04", "conflict", "I can address tension directly without becoming harsh.", False, "conflict_direct", "conflict"),
    _item("CON_05", "conflict", "I sometimes postpone difficult conversations longer than I mean to.", False, "conflict_delay", "conflict"),
    _item("CON_06", "conflict", "I keep the peace even when I disagree strongly.", False, "conflict_avoid", "conflict"),
    _item("CON_07", "conflict", "It helps me to pause and reflect before revisiting conflict.", False, "conflict_delay", "conflict"),
    _item("CON_08", "conflict", "I can state what is bothering me clearly.", False, "conflict_direct", "conflict"),
    _item("CON_09", "conflict", "I would rather let an issue fade than bring it up directly.", False, "conflict_avoid", "conflict"),
    _item("CON_10", "conflict", "A little time can improve how I talk through disagreements.", False, "conflict_delay", "conflict"),
    _item("REG_01", "regulation", "I can settle myself after an emotionally intense moment.", False, "emotional_regulation", "emotional_regulation"),
    _item("REG_02", "regulation", "Strong emotions can take over my reactions.", True, "emotional_regulation", "emotional_regulation", followup_eligible=True),
    _item("REG_03", "regulation", "I usually know what I need to feel grounded again.", False, "emotional_regulation", "emotional_regulation"),
    _item("REG_04", "regulation", "I react first and sort through my feelings later.", True, "emotional_regulation", "emotional_regulation", followup_eligible=True),
    _item("REG_05", "regulation", "I can stay thoughtful during emotionally charged conversations.", False, "emotional_regulation", "emotional_regulation"),
    _item("REG_06", "regulation", "When I feel overwhelmed, it is hard for me to slow down.", True, "emotional_regulation", "emotional_regulation", followup_eligible=True),
    _item("REG_07", "regulation", "I recover fairly quickly after conflict is resolved.", False, "emotional_regulation", "emotional_regulation"),
    _item("REG_08", "regulation", "Stress can make me lose perspective for longer than I want.", True, "emotional_regulation", "emotional_regulation"),
    _item("VAL_01", "values", "Stability and long-term security are important to me.", False, "value_stability", "values", version="v1"),
    _item("VAL_02", "values", "Growth and new experiences are important to me.", False, "value_novelty", "values", version="v1"),
    _item("VAL_03", "values", "I prefer predictable rhythms over frequent surprises.", False, "value_stability", "values"),
    _item("VAL_04", "values", "I feel most engaged when life has room for experimentation.", False, "value_novelty", "values"),
    _item("VAL_05", "values", "A dependable routine helps me feel at ease.", False, "value_stability", "values"),
    _item("VAL_06", "values", "I enjoy relationships that keep evolving in new ways.", False, "value_novelty", "values"),
    _item("VAL_07", "values", "Consistency matters more to me than excitement.", False, "value_stability", "values"),
    _item("VAL_08", "values", "I would trade some predictability for a richer range of experiences.", False, "value_novelty", "values"),
    _item("AFF_01", "affection", "I feel most valued when someone gives me focused attention.", False, "aff_attention", "affection", version="v1"),
    _item("AFF_02", "affection", "Physical closeness is one of the clearest ways I feel cared for.", False, "aff_touch", "affection"),
    _item("AFF_03", "affection", "Verbal appreciation matters a lot to me.", False, "aff_words", "affection"),
    _item("AFF_04", "affection", "Helpful actions mean a lot to me when someone cares about me.", False, "aff_acts", "affection"),
    _item("AFF_05", "affection", "Thoughtful gifts can make me feel especially remembered.", False, "aff_gifts", "affection"),
    _item("AFF_06", "affection", "Uninterrupted quality time helps me feel connected.", False, "aff_attention", "affection"),
    _item("AFF_07", "affection", "Comforting touch can say a lot without words.", False, "aff_touch", "affection"),
    _item("AFF_08", "affection", "Hearing appreciation directly is important to me.", False, "aff_words", "affection"),
    _item("AFF_09", "affection", "Small practical gestures can feel deeply caring to me.", False, "aff_acts", "affection"),
    _item("AFF_10", "affection", "A meaningful gift can stay with me for a long time.", False, "aff_gifts", "affection"),
)


FOLLOWUP_ITEM_BANK: tuple[PsychologyItemDefinition, ...] = (
    _item(
        "FUP_ATT_01",
        "followup",
        "When a relationship feels meaningful, I usually want closeness and independence to be paced carefully rather than quickly.",
        False,
        "independence_need",
        "attachment_followup",
        weight=1.15,
        version="v3",
        item_type="followup_likert",
    ),
    _item(
        "FUP_ATT_02",
        "followup",
        "Even when trust is growing, slower replies can leave me wondering where I stand.",
        False,
        "att_anxiety",
        "attachment_followup",
        weight=1.15,
        version="v3",
        item_type="followup_likert",
    ),
    _item(
        "FUP_CON_01",
        "followup",
        "If a disagreement feels emotionally charged, I still prefer to name the issue instead of stepping around it.",
        False,
        "conflict_direct",
        "conflict_followup",
        weight=1.15,
        version="v3",
        item_type="followup_likert",
    ),
    _item(
        "FUP_REG_01",
        "followup",
        "When I pause and reconsider an answer, it usually reflects careful reflection more than unresolved confusion.",
        False,
        "emotional_regulation",
        "hesitation_followup",
        weight=1.1,
        version="v3",
        item_type="followup_likert",
    ),
    _item(
        "FUP_VAL_01",
        "followup",
        "In relationships, I usually prefer a steady base first and new experiences second.",
        False,
        "value_stability",
        "values_followup",
        weight=1.15,
        version="v3",
        item_type="followup_likert",
    ),
    _item(
        "FUP_DIR_01",
        "followup",
        "I can protect harmony and still say clearly when something needs to change.",
        False,
        "conflict_direct",
        "directness_followup",
        weight=1.15,
        version="v3",
        item_type="followup_likert",
    ),
)


PSYCHOLOGY_ITEM_BANK: tuple[PsychologyItemDefinition, ...] = STANDARD_ITEM_BANK + FOLLOWUP_ITEM_BANK
ITEM_BANK_BY_ID: dict[str, PsychologyItemDefinition] = {item.id: item for item in PSYCHOLOGY_ITEM_BANK}


def get_item_definition(item_id: str) -> PsychologyItemDefinition | None:
    return ITEM_BANK_BY_ID.get(item_id)


def get_active_item_bank() -> tuple[PsychologyItemDefinition, ...]:
    return tuple(item for item in PSYCHOLOGY_ITEM_BANK if item.is_active)


def get_standard_item_bank() -> tuple[PsychologyItemDefinition, ...]:
    return tuple(item for item in STANDARD_ITEM_BANK if item.is_active)


def get_followup_item_bank() -> tuple[PsychologyItemDefinition, ...]:
    return tuple(item for item in FOLLOWUP_ITEM_BANK if item.is_active)


def is_followup_item(item_id: str) -> bool:
    item = get_item_definition(item_id)
    return bool(item and item.item_type != "likert")


def get_target_item_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in get_standard_item_bank():
        counts[item.trait_key] = counts.get(item.trait_key, 0) + 1
    return counts
