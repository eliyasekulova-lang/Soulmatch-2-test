import math
import os
import logging
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import requests
import swisseph as swe
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo

# Astrology constants
PLANETS = [
    swe.SUN,
    swe.MOON,
    swe.MERCURY,
    swe.VENUS,
    swe.MARS,
    swe.JUPITER,
    swe.SATURN,
    swe.URANUS,
    swe.NEPTUNE,
    swe.PLUTO,
    swe.TRUE_NODE,
    swe.CHIRON,
]

ASPECTS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

ELEMENTS = {
    "Aries": "fire", "Leo": "fire", "Sagittarius": "fire",
    "Taurus": "earth", "Virgo": "earth", "Capricorn": "earth",
    "Gemini": "air", "Libra": "air", "Aquarius": "air",
    "Cancer": "water", "Scorpio": "water", "Pisces": "water",
}

MODALITIES = {
    "Aries": "cardinal", "Cancer": "cardinal", "Libra": "cardinal", "Capricorn": "cardinal",
    "Taurus": "fixed", "Leo": "fixed", "Scorpio": "fixed", "Aquarius": "fixed",
    "Gemini": "mutable", "Virgo": "mutable", "Sagittarius": "mutable", "Pisces": "mutable",
}

logger = logging.getLogger("soulmatch.api.astro")


@dataclass
class BirthInput:
    date: str
    time: str
    place: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None


@lru_cache(maxsize=512)
def _geocode(place: str) -> Optional[Tuple[float, float, str]]:
    # Use Nominatim for geocoding (OpenStreetMap)
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": place,
        "format": "json",
        "limit": 1,
    }
    headers = {"User-Agent": "SoulMatch/0.1 (contact: dev@soulmatch.local)"}
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if not data:
        return None
    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])
    return lat, lon, data[0].get("display_name", place)


@lru_cache(maxsize=512)
def _timezone_for(lat: float, lon: float) -> Optional[str]:
    tf = TimezoneFinder()
    return tf.timezone_at(lat=lat, lng=lon)


def _to_utc(date_str: str, time_str: str, tz_name: str) -> datetime:
    local = datetime.fromisoformat(f"{date_str}T{time_str}:00")
    tz = ZoneInfo(tz_name)
    return local.replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))


def _julian_day(dt_utc: datetime) -> float:
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                      dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0)


def _planet_positions(jd: float) -> Dict[int, float]:
    positions = {}
    swiss_flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    moshier_flags = swe.FLG_MOSEPH | swe.FLG_SPEED
    for p in PLANETS:
        try:
            lon, _lat, _dist = swe.calc_ut(jd, p, swiss_flags)[0][:3]
            positions[p] = lon % 360.0
            continue
        except swe.Error:
            # Dev fallback if ephemeris files are unavailable. Production should
            # still provide Swiss ephemeris files via EPHE_PATH.
            logger.warning("swiss_ephemeris_unavailable_fallback_moshier", extra={"planet_id": int(p)})
        try:
            lon, _lat, _dist = swe.calc_ut(jd, p, moshier_flags)[0][:3]
            positions[p] = lon % 360.0
        except swe.Error:
            logger.error("planet_compute_failed_default_zero", extra={"planet_id": int(p)})
            positions[p] = 0.0
    return positions


def _houses(jd: float, lat: float, lon: float) -> Tuple[List[float], Dict[str, float]]:
    # Returns 12 house cusps and angles
    houses, ascmc = swe.houses(jd, lat, lon)
    angles = {
        "asc": ascmc[0] % 360.0,
        "mc": ascmc[1] % 360.0,
        "desc": (ascmc[0] + 180.0) % 360.0,
        "ic": (ascmc[1] + 180.0) % 360.0,
    }
    return houses, angles


def _sign_from_longitude(lon: float) -> str:
    idx = int(lon // 30) % 12
    return SIGNS[idx]


def _aspect_counts(lons: List[float], orb: float = 6.0) -> Dict[str, float]:
    counts = {k: 0 for k in ASPECTS}
    total_pairs = 0
    for i in range(len(lons)):
        for j in range(i + 1, len(lons)):
            total_pairs += 1
            diff = abs(lons[i] - lons[j])
            diff = min(diff, 360.0 - diff)
            for name, angle in ASPECTS.items():
                if abs(diff - angle) <= orb:
                    counts[name] += 1
    if total_pairs == 0:
        return counts
    return {k: v / total_pairs for k, v in counts.items()}


def compute_chart(birth: BirthInput) -> Dict[str, object]:
    lat = birth.latitude
    lon = birth.longitude
    tz = birth.timezone

    if lat is None or lon is None:
        geo = _geocode(birth.place)
        if not geo:
            raise ValueError("geocode_failed")
        lat, lon, _label = geo

    if tz is None:
        tz = _timezone_for(lat, lon)
        if not tz:
            raise ValueError("timezone_failed")

    dt_utc = _to_utc(birth.date, birth.time, tz)
    jd = _julian_day(dt_utc)

    ephe_path = os.getenv("EPHE_PATH", "")
    swe.set_ephe_path(ephe_path)
    positions = _planet_positions(jd)
    houses, angles = _houses(jd, lat, lon)

    return {
        "utc": dt_utc.isoformat(),
        "julian_day": jd,
        "lat": lat,
        "lon": lon,
        "tz": tz,
        "planets": positions,
        "houses": houses,
        "angles": angles,
    }


def chart_to_vector(chart: Dict[str, object], dims: int = 256) -> List[float]:
    planets = chart["planets"]
    lons = [planets[p] for p in PLANETS]

    # 12 planet longitudes normalized
    features: List[float] = [lon / 360.0 for lon in lons]

    # Angles
    angles = chart["angles"]
    features.extend([angles["asc"] / 360.0, angles["mc"] / 360.0,
                     angles["desc"] / 360.0, angles["ic"] / 360.0])

    # Element and modality ratios
    element_counts = {"fire": 0, "earth": 0, "air": 0, "water": 0}
    modality_counts = {"cardinal": 0, "fixed": 0, "mutable": 0}
    for lon in lons:
        sign = _sign_from_longitude(lon)
        element_counts[ELEMENTS[sign]] += 1
        modality_counts[MODALITIES[sign]] += 1

    total = len(lons)
    features.extend([element_counts["fire"] / total, element_counts["earth"] / total,
                     element_counts["air"] / total, element_counts["water"] / total])
    features.extend([modality_counts["cardinal"] / total, modality_counts["fixed"] / total,
                     modality_counts["mutable"] / total])

    # Aspect strengths (5)
    aspect_strengths = _aspect_counts(lons)
    features.extend([
        aspect_strengths["conjunction"],
        aspect_strengths["sextile"],
        aspect_strengths["square"],
        aspect_strengths["trine"],
        aspect_strengths["opposition"],
    ])

    # House concentrations (4 quadrants + 1/4/7/10)
    houses = chart["houses"]
    quadrant_counts = [0, 0, 0, 0]
    key_house_counts = [0, 0, 0, 0]
    for lon in lons:
        house = 1
        for i, cusp in enumerate(houses):
            next_cusp = houses[(i + 1) % 12]
            if cusp <= next_cusp:
                if cusp <= lon < next_cusp:
                    house = i + 1
                    break
            else:
                if lon >= cusp or lon < next_cusp:
                    house = i + 1
                    break
        quadrant_counts[(house - 1) // 3] += 1
        if house in (1, 4, 7, 10):
            key_house_counts[[1, 4, 7, 10].index(house)] += 1

    features.extend([c / total for c in quadrant_counts])
    features.extend([c / total for c in key_house_counts])

    # Derived psychology (simple heuristics)
    attachment = (element_counts["water"] + modality_counts["fixed"]) / (2 * total)
    novelty = (element_counts["fire"] + modality_counts["mutable"]) / (2 * total)
    stability = (element_counts["earth"] + modality_counts["fixed"]) / (2 * total)
    independence = (element_counts["air"] + modality_counts["cardinal"]) / (2 * total)
    features.extend([attachment, novelty, stability, independence, 0.5, 0.5])

    # Behavioral priors (defaults)
    features.extend([0.5] * 6)

    # Composite features (defaults)
    features.extend([0.0] * 6)

    # Pad to dims
    while len(features) < dims:
        features.append(0.0)

    # Normalize
    norm = math.sqrt(sum(v * v for v in features)) or 1.0
    return [v / norm for v in features]
