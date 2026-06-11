from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalyticsEvent, PsychProfile, PsychoAssessmentSession, PsychoItemResponse, PsychoResponse, PsychoScore, User
from app.services.psychology_response_adapter import adapt_assessment_item_responses, adapt_legacy_psycho_responses
from app.services.psychology_scoring_service import LEGACY_PSYCHO_SCORE_KEYS, build_legacy_psycho_score_payload, score_psychology_responses


CANONICAL_V2_DIMENSIONS = [
    "reassurance_need",
    "independence_need",
    "vulnerability_comfort",
    "emotional_regulation",
    "aff_touch",
    "aff_words",
    "aff_acts",
    "aff_gifts",
]

LOVE_LANGUAGE_TO_DIMENSION = {
    "quality_time": "aff_attention",
    "physical_touch": "aff_touch",
    "words_of_affirmation": "aff_words",
    "acts_of_service": "aff_acts",
    "receiving_gifts": "aff_gifts",
    "gifts": "aff_gifts",
}


@dataclass(frozen=True)
class CanonicalPsychBackfillResult:
    user_id: str
    status: str
    source: str
    canonical_dimension_version: str | None
    canonical_dimensions: list[str]


def backfill_canonical_psycho_scores(
    db: Session,
    *,
    user_ids: list[str] | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    include_canonical_v2: bool = False,
) -> list[CanonicalPsychBackfillResult]:
    target_user_ids = user_ids or list(db.scalars(select(User.id).order_by(User.id)).all())
    if limit is not None:
        target_user_ids = target_user_ids[:limit]

    results: list[CanonicalPsychBackfillResult] = []
    for user_id in target_user_ids:
        row = db.get(PsychoScore, user_id)
        quality_flags = {} if row is None else dict(row.quality_flags or {})
        if not include_canonical_v2 and quality_flags.get("canonical_dimension_version") == "v2":
            results.append(
                CanonicalPsychBackfillResult(
                    user_id=user_id,
                    status="skipped_already_v2",
                    source="existing",
                    canonical_dimension_version="v2",
                    canonical_dimensions=list(quality_flags.get("canonical_dimensions") or CANONICAL_V2_DIMENSIONS),
                )
            )
            continue

        profile = db.get(PsychProfile, user_id)
        response_bundle = _load_best_response_bundle(db, user_id=user_id)
        updated_row, source = _apply_backfill(
            db,
            user_id=user_id,
            psycho_score=row,
            psych_profile=profile,
            response_bundle=response_bundle,
            dry_run=dry_run,
        )
        result_quality_flags = {} if updated_row is None else dict(updated_row.quality_flags or {})
        results.append(
            CanonicalPsychBackfillResult(
                user_id=user_id,
                status="updated" if updated_row is not None and source != "none" else "skipped_no_supported_sources",
                source=source,
                canonical_dimension_version=result_quality_flags.get("canonical_dimension_version"),
                canonical_dimensions=list(result_quality_flags.get("canonical_dimensions") or []),
            )
        )
    if dry_run:
        db.rollback()
    else:
        db.flush()
    return results


def _apply_backfill(
    db: Session,
    *,
    user_id: str,
    psycho_score: PsychoScore | None,
    psych_profile: PsychProfile | None,
    response_bundle: tuple[dict, str, int] | None,
    dry_run: bool,
) -> tuple[PsychoScore | None, str]:
    row = psycho_score
    sources: dict[str, str] = {}
    canonical_dimensions = set()
    scored = None

    if response_bundle is not None:
        normalized_responses, response_source, answered_count = response_bundle
        if answered_count > 0:
            scored = score_psychology_responses(normalized_responses)
            sources["response_source"] = response_source

    if row is None and scored is None:
        return None, "none"

    if row is None:
        if not _has_full_legacy_coverage(scored.dimension_counts if scored else {}):
            return None, "none"
        row = PsychoScore(user_id=user_id)
        if not dry_run:
            db.add(row)

    existing_flags = dict(row.quality_flags or {})
    existing_dimensions = set(existing_flags.get("canonical_dimensions") or [])
    canonical_dimensions.update(existing_dimensions)
    dimension_sources = dict(existing_flags.get("canonical_dimension_sources") or {})

    if scored is not None and _has_full_legacy_coverage(scored.dimension_counts):
        legacy_traits, legacy_vector, legacy_uncertainty = build_legacy_psycho_score_payload(scored)
        row.o = legacy_traits["O"]
        row.c = legacy_traits["C"]
        row.e = legacy_traits["E"]
        row.a = legacy_traits["A"]
        row.n = legacy_traits["N"]
        row.att_anxiety = legacy_traits["att_anxiety"]
        row.att_avoid = legacy_traits["att_avoid"]
        row.conflict_direct = legacy_traits["conflict_direct"]
        row.conflict_avoid = legacy_traits["conflict_avoid"]
        row.conflict_delay = legacy_traits["conflict_delay"]
        row.value_stability = legacy_traits["value_stability"]
        row.value_novelty = legacy_traits["value_novelty"]
        row.aff_attention = legacy_traits["aff_attention"]
        row.psycho_vector = legacy_vector
        row.psycho_uncertainty = legacy_uncertainty

    if scored is not None:
        for dimension in CANONICAL_V2_DIMENSIONS:
            if scored.dimension_counts.get(dimension, 0) > 0:
                setattr(row, dimension, float(scored.traits[dimension]))
                canonical_dimensions.add(dimension)
                dimension_sources[dimension] = sources["response_source"]

    if psych_profile is not None and "independence_need" not in canonical_dimensions:
        row.independence_need = float(psych_profile.boundaries_preference)
        canonical_dimensions.add("independence_need")
        dimension_sources["independence_need"] = "psych_profile.boundaries_preference"

    if psych_profile is not None:
        affection_dimension = LOVE_LANGUAGE_TO_DIMENSION.get(str(psych_profile.love_language or "").strip().lower())
        if affection_dimension in {"aff_touch", "aff_words", "aff_acts", "aff_gifts"} and affection_dimension not in canonical_dimensions:
            setattr(row, affection_dimension, 0.75)
            canonical_dimensions.add(affection_dimension)
            dimension_sources[affection_dimension] = "psych_profile.love_language"

    quality_flags = dict(existing_flags)
    quality_flags["canonical_dimensions"] = sorted(canonical_dimensions)
    quality_flags["canonical_dimension_sources"] = dimension_sources
    quality_flags["canonical_backfill_at"] = datetime.utcnow().isoformat()
    if canonical_dimensions >= set(CANONICAL_V2_DIMENSIONS):
        quality_flags["canonical_dimension_version"] = "v2"
    elif canonical_dimensions:
        quality_flags["canonical_dimension_version"] = "v2_partial"
    row.quality_flags = quality_flags
    row.computed_at = datetime.utcnow()
    if dry_run:
        return row, _summarize_sources(dimension_sources)
    db.flush()
    return row, _summarize_sources(dimension_sources)


def _load_best_response_bundle(db: Session, *, user_id: str) -> tuple[dict, str, int] | None:
    session_rows = db.scalars(
        select(PsychoAssessmentSession)
        .where(PsychoAssessmentSession.user_id == user_id)
        .order_by(PsychoAssessmentSession.completed_at.desc(), PsychoAssessmentSession.created_at.desc())
    ).all()
    best_session_responses: dict | None = None
    best_session_source = "none"
    best_session_count = 0
    for session in session_rows:
        rows = db.scalars(
            select(PsychoItemResponse)
            .where(PsychoItemResponse.user_id == user_id, PsychoItemResponse.session_id == session.id)
            .order_by(PsychoItemResponse.id.asc())
        ).all()
        normalized = adapt_assessment_item_responses(rows)
        answered = _count_answered(normalized)
        if answered > best_session_count:
            best_session_responses = normalized
            best_session_source = f"psycho_item_responses:{session.id}"
            best_session_count = answered

    legacy_rows = db.scalars(
        select(PsychoResponse).where(PsychoResponse.user_id == user_id).order_by(PsychoResponse.item_id.asc())
    ).all()
    legacy_normalized = adapt_legacy_psycho_responses(legacy_rows)
    legacy_count = _count_answered(legacy_normalized)

    if best_session_count == 0 and legacy_count == 0:
        return None
    if best_session_count >= legacy_count:
        return best_session_responses or {}, best_session_source, best_session_count
    return legacy_normalized, "psycho_response_legacy", legacy_count


def _count_answered(normalized_responses: dict) -> int:
    count = 0
    for row in normalized_responses.values():
        if row.skipped:
            continue
        if row.considered_answer_value is not None or row.final_answer_value is not None or row.answer_value is not None:
            count += 1
    return count


def _has_full_legacy_coverage(dimension_counts: dict[str, int]) -> bool:
    return all(dimension_counts.get(key, 0) > 0 for key in LEGACY_PSYCHO_SCORE_KEYS)


def _summarize_sources(dimension_sources: dict[str, str]) -> str:
    if not dimension_sources:
        return "none"
    return ",".join(sorted(set(dimension_sources.values())))


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill canonical PsychoScore v2 dimensions from safe historical sources.")
    parser.add_argument("--user-id", dest="user_ids", action="append", default=None, help="User id to backfill. Repeatable.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum users to process.")
    parser.add_argument("--dry-run", action="store_true", help="Compute backfill results without persisting.")
    parser.add_argument("--include-v2", action="store_true", help="Re-evaluate already v2 rows.")
    parser.add_argument("--database-url", help="Optional database URL override for the backfill session.")
    args = parser.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    from app.database import SessionLocal

    try:
        with SessionLocal() as db:
            results = backfill_canonical_psycho_scores(
                db,
                user_ids=args.user_ids,
                limit=args.limit,
                dry_run=args.dry_run,
                include_canonical_v2=args.include_v2,
            )
            if args.dry_run:
                db.rollback()
            else:
                db.add(
                    AnalyticsEvent(
                        user_id=None,
                        event_name="psychology_backfill_completed",
                        event_payload={
                            "processed": len(results),
                            "updated": sum(1 for result in results if result.status == "updated"),
                            "skipped_already_v2": sum(1 for result in results if result.status == "skipped_already_v2"),
                            "skipped_no_supported_sources": sum(1 for result in results if result.status == "skipped_no_supported_sources"),
                        },
                    )
                )
                db.commit()
    except Exception as exc:
        print(f"Psychology Backfill Error: {exc}", file=sys.stderr)
        print(
            "Hint: export a reachable PostgreSQL DATABASE_URL (for staging or local validation) before running this backfill.",
            file=sys.stderr,
        )
        return 1

    for result in results:
        print(
            f"{result.user_id}\t{result.status}\t{result.source}\t"
            f"{result.canonical_dimension_version or 'none'}\t{','.join(result.canonical_dimensions)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
