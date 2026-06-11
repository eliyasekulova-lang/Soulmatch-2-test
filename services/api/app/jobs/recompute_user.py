from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import UserProfileState
from app.services.match_orchestration_service import compute_orchestrated_matches, replace_match_v2_rows


def recompute_matches_for_user(db: Session, user_id: str, top_k: int = 20) -> int:
    state = db.get(UserProfileState, user_id)
    if not state or state.stage != "eligible":
        return 0

    rows = compute_orchestrated_matches(
        db,
        user_id=user_id,
        mode="romance",
        match_mode="destiny",
    )
    created = replace_match_v2_rows(db, user_id=user_id, rows=rows, top_k=top_k)
    db.commit()
    return created
