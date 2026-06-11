from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.jobs.seed_psycho_items import seed_psycho_items
from app.models import (
    AnalyticsEvent,
    AuthUser,
    BehaviorFeature,
    MatchV2,
    PsychoAssessmentSession,
    PsychoDerivedPattern,
    PsychoItem,
    PsychoItemResponse,
    PsychoReport,
    PsychoScore,
    User,
    UserProfileState,
)
from app.psychology_item_bank import get_standard_item_bank
from app.services.assessment_flow_service import (
    ONBOARDING_ASSESSMENT_MODE,
    finalize_assessment,
    start_or_resume_assessment_session,
    upsert_session_answer,
)
from app.services.derived_patterns_service import clamp


SYNTHETIC_TEST_USER_STATUS = "synthetic_test"
SYNTHETIC_TEST_EMAIL_DOMAIN = "synthetic.soulmatch.test"


@dataclass(frozen=True)
class SyntheticPsychSeedProfile:
    slug: str
    display_name: str
    traits: dict[str, float]
    behavior: dict[str, float]


@dataclass(frozen=True)
class SyntheticPsychSeedResult:
    user_id: str
    session_id: str
    psycho_score_version: str | None
    report_version: str | None


SEED_PROFILES: tuple[SyntheticPsychSeedProfile, ...] = (
    SyntheticPsychSeedProfile(
        "secure-steady",
        "Synthetic Secure Steady",
        {
            "O": 0.52,
            "C": 0.74,
            "E": 0.48,
            "A": 0.72,
            "N": 0.28,
            "att_anxiety": 0.24,
            "att_avoid": 0.26,
            "reassurance_need": 0.30,
            "independence_need": 0.44,
            "vulnerability_comfort": 0.78,
            "conflict_direct": 0.70,
            "conflict_avoid": 0.24,
            "conflict_delay": 0.36,
            "emotional_regulation": 0.76,
            "value_stability": 0.72,
            "value_novelty": 0.36,
            "aff_attention": 0.68,
            "aff_touch": 0.52,
            "aff_words": 0.58,
            "aff_acts": 0.64,
            "aff_gifts": 0.30,
        },
        {
            "response_consistency": 0.84,
            "response_delay_var": 0.26,
            "initiative_ratio": 0.48,
            "conversation_balance": 0.56,
            "engagement_stability": 0.78,
            "boundary_respect": 0.86,
            "emotional_variability": 0.30,
        },
    ),
    SyntheticPsychSeedProfile(
        "warm-expressive",
        "Synthetic Warm Expressive",
        {
            "O": 0.66,
            "C": 0.56,
            "E": 0.76,
            "A": 0.80,
            "N": 0.34,
            "att_anxiety": 0.36,
            "att_avoid": 0.20,
            "reassurance_need": 0.56,
            "independence_need": 0.34,
            "vulnerability_comfort": 0.82,
            "conflict_direct": 0.62,
            "conflict_avoid": 0.30,
            "conflict_delay": 0.28,
            "emotional_regulation": 0.68,
            "value_stability": 0.48,
            "value_novelty": 0.64,
            "aff_attention": 0.84,
            "aff_touch": 0.62,
            "aff_words": 0.82,
            "aff_acts": 0.56,
            "aff_gifts": 0.28,
        },
        {
            "response_consistency": 0.80,
            "response_delay_var": 0.32,
            "initiative_ratio": 0.62,
            "conversation_balance": 0.60,
            "engagement_stability": 0.76,
            "boundary_respect": 0.82,
            "emotional_variability": 0.38,
        },
    ),
    SyntheticPsychSeedProfile(
        "independent-explorer",
        "Synthetic Independent Explorer",
        {
            "O": 0.82,
            "C": 0.54,
            "E": 0.62,
            "A": 0.52,
            "N": 0.40,
            "att_anxiety": 0.22,
            "att_avoid": 0.62,
            "reassurance_need": 0.24,
            "independence_need": 0.80,
            "vulnerability_comfort": 0.48,
            "conflict_direct": 0.54,
            "conflict_avoid": 0.36,
            "conflict_delay": 0.54,
            "emotional_regulation": 0.66,
            "value_stability": 0.34,
            "value_novelty": 0.84,
            "aff_attention": 0.42,
            "aff_touch": 0.34,
            "aff_words": 0.44,
            "aff_acts": 0.40,
            "aff_gifts": 0.30,
        },
        {
            "response_consistency": 0.76,
            "response_delay_var": 0.34,
            "initiative_ratio": 0.58,
            "conversation_balance": 0.50,
            "engagement_stability": 0.70,
            "boundary_respect": 0.84,
            "emotional_variability": 0.34,
        },
    ),
    SyntheticPsychSeedProfile(
        "reflective-stable",
        "Synthetic Reflective Stable",
        {
            "O": 0.44,
            "C": 0.78,
            "E": 0.34,
            "A": 0.70,
            "N": 0.26,
            "att_anxiety": 0.28,
            "att_avoid": 0.38,
            "reassurance_need": 0.34,
            "independence_need": 0.48,
            "vulnerability_comfort": 0.66,
            "conflict_direct": 0.58,
            "conflict_avoid": 0.26,
            "conflict_delay": 0.46,
            "emotional_regulation": 0.80,
            "value_stability": 0.82,
            "value_novelty": 0.24,
            "aff_attention": 0.58,
            "aff_touch": 0.44,
            "aff_words": 0.54,
            "aff_acts": 0.78,
            "aff_gifts": 0.26,
        },
        {
            "response_consistency": 0.88,
            "response_delay_var": 0.22,
            "initiative_ratio": 0.42,
            "conversation_balance": 0.54,
            "engagement_stability": 0.82,
            "boundary_respect": 0.88,
            "emotional_variability": 0.24,
        },
    ),
    SyntheticPsychSeedProfile(
        "direct-repair",
        "Synthetic Direct Repair",
        {
            "O": 0.58,
            "C": 0.66,
            "E": 0.68,
            "A": 0.60,
            "N": 0.42,
            "att_anxiety": 0.34,
            "att_avoid": 0.30,
            "reassurance_need": 0.40,
            "independence_need": 0.42,
            "vulnerability_comfort": 0.70,
            "conflict_direct": 0.84,
            "conflict_avoid": 0.18,
            "conflict_delay": 0.22,
            "emotional_regulation": 0.68,
            "value_stability": 0.54,
            "value_novelty": 0.52,
            "aff_attention": 0.52,
            "aff_touch": 0.58,
            "aff_words": 0.62,
            "aff_acts": 0.48,
            "aff_gifts": 0.24,
        },
        {
            "response_consistency": 0.82,
            "response_delay_var": 0.28,
            "initiative_ratio": 0.56,
            "conversation_balance": 0.52,
            "engagement_stability": 0.74,
            "boundary_respect": 0.80,
            "emotional_variability": 0.42,
        },
    ),
    SyntheticPsychSeedProfile(
        "gentle-space",
        "Synthetic Gentle Space",
        {
            "O": 0.54,
            "C": 0.60,
            "E": 0.40,
            "A": 0.76,
            "N": 0.38,
            "att_anxiety": 0.42,
            "att_avoid": 0.50,
            "reassurance_need": 0.46,
            "independence_need": 0.64,
            "vulnerability_comfort": 0.54,
            "conflict_direct": 0.42,
            "conflict_avoid": 0.44,
            "conflict_delay": 0.62,
            "emotional_regulation": 0.62,
            "value_stability": 0.62,
            "value_novelty": 0.42,
            "aff_attention": 0.74,
            "aff_touch": 0.36,
            "aff_words": 0.64,
            "aff_acts": 0.58,
            "aff_gifts": 0.30,
        },
        {
            "response_consistency": 0.78,
            "response_delay_var": 0.30,
            "initiative_ratio": 0.40,
            "conversation_balance": 0.58,
            "engagement_stability": 0.72,
            "boundary_respect": 0.86,
            "emotional_variability": 0.36,
        },
    ),
)


def seed_canonical_psych_test_users(
    db: Session,
    *,
    include_reports: bool = True,
    limit: int | None = None,
) -> list[SyntheticPsychSeedResult]:
    seed_psycho_items(db)
    profiles = list(SEED_PROFILES[:limit] if limit is not None else SEED_PROFILES)
    item_map = {row.id: row for row in db.query(PsychoItem).filter(PsychoItem.is_active.is_(True)).all()}
    standard_items = [item_map[item.id] for item in get_standard_item_bank() if item.id in item_map]

    results: list[SyntheticPsychSeedResult] = []
    for index, profile in enumerate(profiles):
        user_id = f"usr-synth-psych-{profile.slug}"
        auth_email = f"synthetic+psych-{profile.slug}@{SYNTHETIC_TEST_EMAIL_DOMAIN}"
        _clear_synthetic_user_artifacts(db, user_id=user_id)
        db.flush()
        _upsert_synthetic_identity(db, user_id=user_id, email=auth_email, display_name=profile.display_name)
        # Parent identity rows must exist before inserting dependent psych and
        # behavior artifacts that reference users/auth_users via foreign keys.
        db.flush()
        _upsert_behavior_feature(db, user_id=user_id, behavior=profile.behavior)
        db.flush()

        session = start_or_resume_assessment_session(
            db,
            user_id=user_id,
            assessment_mode=ONBOARDING_ASSESSMENT_MODE,
            version="v3_prelaunch_seed",
            device_type="synthetic_seed",
        )
        answered_at = datetime.utcnow()
        for offset, item in enumerate(standard_items):
            answer_value = _answer_for_item(item=item, trait_value=profile.traits[item.trait_key])
            response_time_ms = 1100 + (index * 40) + (offset % 5) * 25
            upsert_session_answer(
                db,
                session=session,
                item_id=item.id,
                answer_value=answer_value,
                first_answer_value=answer_value,
                considered_answer_value=answer_value,
                changed_answer_count=0,
                response_time_ms=response_time_ms,
                started_at=answered_at,
                answered_at=answered_at,
                returned_to_question=False,
                skipped=False,
                device_type="synthetic_seed",
            )

        session.status = "in_progress"
        session.completed_at = None
        finalized = finalize_assessment(db, session=session, item_map=item_map)
        score = db.get(PsychoScore, user_id)
        report_version = None if (not include_reports or finalized.report is None) else finalized.report.report_version
        results.append(
            SyntheticPsychSeedResult(
                user_id=user_id,
                session_id=finalized.session.id,
                psycho_score_version=None if score is None else dict(score.quality_flags or {}).get("canonical_dimension_version"),
                report_version=report_version,
            )
        )

    db.flush()
    return results


def _clear_synthetic_user_artifacts(db: Session, *, user_id: str) -> None:
    db.execute(delete(MatchV2).where((MatchV2.user_id == user_id) | (MatchV2.other_user_id == user_id)))
    db.execute(delete(PsychoItemResponse).where(PsychoItemResponse.user_id == user_id))
    db.execute(delete(PsychoAssessmentSession).where(PsychoAssessmentSession.user_id == user_id))
    db.execute(delete(PsychoDerivedPattern).where(PsychoDerivedPattern.user_id == user_id))
    db.execute(delete(PsychoReport).where(PsychoReport.user_id == user_id))
    db.execute(delete(PsychoScore).where(PsychoScore.user_id == user_id))
    db.execute(delete(UserProfileState).where(UserProfileState.user_id == user_id))
    db.execute(delete(BehaviorFeature).where(BehaviorFeature.user_id == user_id))


def _upsert_synthetic_identity(db: Session, *, user_id: str, email: str, display_name: str) -> None:
    auth_user = db.get(AuthUser, user_id)
    if auth_user is None:
        auth_user = AuthUser(id=user_id, email=email, password_hash="synthetic-seeded-hash")
        db.add(auth_user)
    else:
        auth_user.email = email

    user = db.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            name=display_name,
            email=email,
            birth_date="1992-04-14",
            birth_time="09:30",
            birth_place="Toronto, Canada",
            goals=["romance"],
            matching_preference="psych_behavior",
            status=SYNTHETIC_TEST_USER_STATUS,
        )
        db.add(user)
    else:
        user.name = display_name
        user.email = email
        user.status = SYNTHETIC_TEST_USER_STATUS
        user.matching_preference = "psych_behavior"
        user.birth_date = "1992-04-14"
        user.birth_time = "09:30"
        user.birth_place = "Toronto, Canada"
        user.goals = ["romance"]


def _upsert_behavior_feature(db: Session, *, user_id: str, behavior: dict[str, float]) -> None:
    row = db.get(BehaviorFeature, user_id)
    if row is None:
        row = BehaviorFeature(user_id=user_id)
        db.add(row)
    row.response_consistency = float(behavior["response_consistency"])
    row.response_delay_var = float(behavior["response_delay_var"])
    row.initiative_ratio = float(behavior["initiative_ratio"])
    row.conversation_balance = float(behavior["conversation_balance"])
    row.engagement_stability = float(behavior["engagement_stability"])
    row.boundary_respect = float(behavior["boundary_respect"])
    row.emotional_variability = float(behavior["emotional_variability"])
    row.behavior_vector = [
        row.response_consistency,
        clamp(1.0 - row.response_delay_var),
        row.initiative_ratio,
        row.conversation_balance,
        row.engagement_stability,
        row.boundary_respect,
    ]
    row.behavior_uncertainty = [0.16] * 6
    row.computed_at = datetime.utcnow()


def _answer_for_item(*, item: PsychoItem, trait_value: float) -> int:
    score = clamp(float(trait_value))
    base = int(round(score * 4.0)) + 1
    if item.reverse_key:
        return max(1, min(5, 6 - base))
    return max(1, min(5, base))


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed deterministic synthetic canonical psychology users for staging/testing.")
    parser.add_argument("--database-url", help="Optional database URL override for the seed session.")
    parser.add_argument("--limit", type=int, default=None, help="Limit seeded synthetic users.")
    args = parser.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    from app.database import SessionLocal

    try:
        with SessionLocal() as db:
            results = seed_canonical_psych_test_users(db, limit=args.limit)
            db.add(
                AnalyticsEvent(
                    user_id=None,
                    event_name="psychology_synthetic_seed_completed",
                    event_payload={
                        "seeded_users": len(results),
                        "user_ids": [result.user_id for result in results],
                    },
                )
            )
            db.commit()
    except Exception as exc:
        print(f"Psychology Synthetic Seed Error: {exc}", file=sys.stderr)
        print(
            "Hint: provide a reachable DATABASE_URL for staging/testing before running this seed command.",
            file=sys.stderr,
        )
        return 1

    for result in results:
        print(
            f"{result.user_id}\t{result.session_id}\t{result.psycho_score_version or 'none'}\t{result.report_version or 'none'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
