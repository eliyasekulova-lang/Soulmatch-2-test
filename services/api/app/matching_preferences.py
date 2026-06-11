MATCHING_PREFERENCE_PSYCH_BEHAVIOR = "psych_behavior"
MATCHING_PREFERENCE_PSYCH_BEHAVIOR_ASTRO = "psych_behavior_astro"

DEFAULT_MATCHING_PREFERENCE = MATCHING_PREFERENCE_PSYCH_BEHAVIOR_ASTRO
MATCHING_PREFERENCE_VALUES = {
    MATCHING_PREFERENCE_PSYCH_BEHAVIOR,
    MATCHING_PREFERENCE_PSYCH_BEHAVIOR_ASTRO,
}


def normalize_matching_preference(value: str | None) -> str:
    if value in MATCHING_PREFERENCE_VALUES:
        return str(value)
    return DEFAULT_MATCHING_PREFERENCE


def preference_requires_astro(value: str | None) -> bool:
    return normalize_matching_preference(value) == MATCHING_PREFERENCE_PSYCH_BEHAVIOR_ASTRO
