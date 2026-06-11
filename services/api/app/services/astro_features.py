from __future__ import annotations

from datetime import datetime

from app.astro import ASPECTS, ELEMENTS, MODALITIES, SIGNS, BirthInput, compute_chart

ELEMENT_ORDER = ["fire", "earth", "air", "water"]
MODALITY_ORDER = ["cardinal", "fixed", "mutable"]
PERSONAL_PLANETS = ["sun", "moon", "venus", "mars"]
PLANET_IDS = {
    "sun": 0,
    "moon": 1,
    "mercury": 2,
    "venus": 3,
    "mars": 4,
    "jupiter": 5,
    "saturn": 6,
}


def _sign_index(longitude: float) -> int:
    return int((longitude % 360.0) // 30)


def _house_for_longitude(longitude: float, houses: list[float]) -> int:
    if not houses:
        return 1
    for i, cusp in enumerate(houses):
        next_cusp = houses[(i + 1) % 12]
        if cusp <= next_cusp:
            if cusp <= longitude < next_cusp:
                return i + 1
        else:
            if longitude >= cusp or longitude < next_cusp:
                return i + 1
    return 1


def _aspect_features(longitudes: dict[str, float]) -> tuple[list[dict[str, float | str]], list[float]]:
    aspects: list[dict[str, float | str]] = []
    buckets = [0.0] * 16
    planet_keys = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
    aspect_names = list(ASPECTS.keys())

    for i, p1 in enumerate(planet_keys):
        for p2 in planet_keys[i + 1 :]:
            l1 = longitudes[p1]
            l2 = longitudes[p2]
            diff = abs(l1 - l2)
            diff = min(diff, 360.0 - diff)
            for aspect_name, angle in ASPECTS.items():
                orb = abs(diff - angle)
                max_orb = 8.0
                if orb > max_orb:
                    continue
                strength = max(0.0, min(1.0, 1.0 - (orb / max_orb)))
                aspects.append(
                    {
                        "p1": p1,
                        "p2": p2,
                        "type": aspect_name,
                        "orb": round(orb, 3),
                        "strength": round(strength, 4),
                    }
                )
                bucket_ix = (PLANET_IDS[p1] + PLANET_IDS[p2] + aspect_names.index(aspect_name)) % len(buckets)
                buckets[bucket_ix] = max(buckets[bucket_ix], strength)

    return aspects, buckets


def compute_natal_chart_features(
    birth_date: str,
    birth_time: str,
    birth_place_name: str,
    lat: float,
    lon: float,
    timezone_iana: str,
) -> dict[str, object]:
    chart = compute_chart(
        BirthInput(
            date=birth_date,
            time=birth_time,
            place=birth_place_name,
            latitude=lat,
            longitude=lon,
            timezone=timezone_iana,
        )
    )

    raw_planets = chart.get("planets", {})
    houses = chart.get("houses", [])
    angles = chart.get("angles", {})

    named = {
        "sun": float(raw_planets.get(0, 0.0)),
        "moon": float(raw_planets.get(1, 0.0)),
        "mercury": float(raw_planets.get(2, 0.0)),
        "venus": float(raw_planets.get(3, 0.0)),
        "mars": float(raw_planets.get(4, 0.0)),
        "jupiter": float(raw_planets.get(5, 0.0)),
        "saturn": float(raw_planets.get(6, 0.0)),
    }

    planets_payload = {}
    elements = []
    modalities = []
    personal_house_norms = []

    for key in PERSONAL_PLANETS:
        lon_value = named[key]
        sign_idx = _sign_index(lon_value)
        sign = SIGNS[sign_idx]
        element = ELEMENTS[sign]
        modality = MODALITIES[sign]
        house = _house_for_longitude(lon_value, houses)

        planets_payload[key] = {
            "sign": sign_idx,
            "deg": round(lon_value % 30.0, 4),
            "house": house,
            "element": element,
            "modality": modality,
        }
        elements.append(element)
        modalities.append(modality)
        personal_house_norms.append(house / 12.0)

    aspects, aspect_buckets = _aspect_features(named)

    vector: list[float] = []
    for element in elements:
        vector.extend([1.0 if element == candidate else 0.0 for candidate in ELEMENT_ORDER])
    for modality in modalities:
        vector.extend([1.0 if modality == candidate else 0.0 for candidate in MODALITY_ORDER])
    vector.extend(personal_house_norms)
    vector.extend(aspect_buckets)

    while len(vector) < 48:
        vector.append(0.0)
    if len(vector) > 48:
        vector = vector[:48]

    asc = float(angles.get("asc", 0.0))
    features = {
        "attachment_pattern_proxy": round((vector[0] + vector[4] + vector[8] + vector[12]) / 4.0, 4),
        "emotional_volatility_proxy": round((vector[17] + vector[20] + vector[35]) / 3.0, 4),
        "relationship_orientation_proxy": round((vector[24] + vector[25] + vector[26] + vector[27]) / 4.0, 4),
    }

    return {
        "asc_sign": _sign_index(asc),
        "asc_deg": round(asc % 30.0, 4),
        "planets": planets_payload,
        "aspects": aspects,
        "astro_features": features,
        "astro_vector": [round(float(value), 6) for value in vector],
        "computed_at": datetime.utcnow(),
    }
