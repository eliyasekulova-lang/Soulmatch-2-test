from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import PsychoItem
from app.psychology_item_bank import PSYCHOLOGY_ITEM_BANK


def seed_psycho_items(db: Session) -> int:
    existing_rows = {item.id: item for item in db.query(PsychoItem).all()}
    touched = 0

    for item in PSYCHOLOGY_ITEM_BANK:
        row = existing_rows.get(item.id)
        if row is None:
            row = PsychoItem(id=item.id)
            db.add(row)
            existing_rows[item.id] = row
            touched += 1

        before = (
            row.module,
            row.prompt,
            row.reverse_key,
            row.trait_key,
            row.weight,
            row.item_type,
            row.version,
            row.dimension_group,
            row.is_active,
            row.followup_eligible,
        )

        row.module = item.module
        row.prompt = item.prompt
        row.reverse_key = item.reverse_key
        row.trait_key = item.trait_key
        row.weight = item.weight
        row.item_type = item.item_type
        row.version = item.version
        row.dimension_group = item.dimension_group
        row.is_active = item.is_active
        row.followup_eligible = item.followup_eligible

        after = (
            row.module,
            row.prompt,
            row.reverse_key,
            row.trait_key,
            row.weight,
            row.item_type,
            row.version,
            row.dimension_group,
            row.is_active,
            row.followup_eligible,
        )
        if before != after and item.id in existing_rows and before[0] is not None:
            touched += 1

    if touched:
        db.commit()
    return touched
