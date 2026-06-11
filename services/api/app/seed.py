from typing import Any

from sqlalchemy.orm import Session

from .astro import BirthInput, chart_to_vector, compute_chart
from .models import AstroVector, User


DEMO_CANDIDATES: list[dict[str, Any]] = [
    {
        "id": "cand-toronto-001",
        "name": "Ari",
        "email": None,
        "birth": {
            "date": "1998-07-15",
            "time": "08:20",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance", "friendship"],
    },
    {
        "id": "cand-montreal-001",
        "name": "Noah",
        "email": None,
        "birth": {
            "date": "1996-02-04",
            "time": "21:40",
            "place": "Montreal, Canada",
            "latitude": 45.5017,
            "longitude": -73.5673,
            "timezone": "America/Toronto",
        },
        "goals": ["romance", "friendship"],
    },
    {
        "id": "cand-nyc-001",
        "name": "Leila",
        "email": None,
        "birth": {
            "date": "1999-11-29",
            "time": "13:10",
            "place": "New York, USA",
            "latitude": 40.7128,
            "longitude": -74.006,
            "timezone": "America/New_York",
        },
        "goals": ["romance", "friendship"],
    },
    {
        "id": "cand-london-001",
        "name": "Maya",
        "email": None,
        "birth": {
            "date": "1997-04-08",
            "time": "06:55",
            "place": "London, UK",
            "latitude": 51.5072,
            "longitude": -0.1276,
            "timezone": "Europe/London",
        },
        "goals": ["romance", "friendship"],
    },
]


def seed_demo_candidates(db: Session) -> int:
    inserted = 0
    for candidate in DEMO_CANDIDATES:
        user = db.get(User, candidate["id"])
        if not user:
            birth = candidate["birth"]
            user = User(
                id=candidate["id"],
                name=candidate["name"],
                email=candidate["email"],
                birth_date=birth["date"],
                birth_time=birth["time"],
                birth_place=birth["place"],
                birth_latitude=birth["latitude"],
                birth_longitude=birth["longitude"],
                birth_timezone=birth["timezone"],
                goals=candidate["goals"],
            )
            db.add(user)
            # Ensure parent user row exists before inserting dependent vector row.
            db.flush()
            inserted += 1

        vector = db.get(AstroVector, candidate["id"])
        if not vector:
            birth = candidate["birth"]
            chart = compute_chart(
                BirthInput(
                    date=birth["date"],
                    time=birth["time"],
                    place=birth["place"],
                    latitude=birth["latitude"],
                    longitude=birth["longitude"],
                    timezone=birth["timezone"],
                )
            )
            db.add(
                AstroVector(
                    user_id=candidate["id"],
                    vector=chart_to_vector(chart, dims=256),
                    schema_version="v1",
                )
            )
    db.commit()
    return inserted
