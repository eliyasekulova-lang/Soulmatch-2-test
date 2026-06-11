from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.matching_preferences import preference_requires_astro
from app.models import (
    AnalyticsEvent,
    AstroVector,
    BehaviorFeature,
    MatchResult,
    MatchV2,
    PsychProfile,
    PsychoDerivedPattern,
    PsychoScore,
    User,
    UserProfileState,
)
from app.jobs.backfill_canonical_psych_scores import backfill_canonical_psycho_scores

from .compatibility_dynamics_service import build_matching_psych_data, compute_compatibility_dynamics
from .matching import explanation_highlights, rank_pair_score, score_pair
from .psycho_scoring import clamp
from .weight_tuning import derive_feedback_weight_multipliers


@dataclass(frozen=True)
class OrchestratedMatchRow:
    other_user_id: str
    candidate_name: str
    candidate_city: str
    psycho_score: float
    astro_score: float
    behavior_score: float
    compatibility_score: float
    rank_score: float
    confidence: float
    dynamics_payload: dict[str, object]
    explanation: dict[str, object]
    highlights: list[str]


def _safe_norm(value: float) -> float:
    return max(0.0, min(1.0, value))


def _alignment_score(source_user: User | None, candidate_user: User | None) -> float:
    if source_user is None or candidate_user is None:
        return 0.5
    source_goals = set(source_user.goals or [])
    candidate_goals = set(candidate_user.goals or [])
    if not source_goals and not candidate_goals:
        return 0.5
    overlap = len(source_goals.intersection(candidate_goals))
    union = max(1, len(source_goals.union(candidate_goals)))
    return _safe_norm(overlap / union)


def _compose_total(
    *,
    astro_score: float,
    psycho_score: float,
    behavior_score: float,
    alignment_score: float,
    match_mode: str,
    include_astro: bool,
) -> float:
    if match_mode == "destiny":
        weights = {"astro": 0.25, "psych": 0.30, "behavior": 0.25, "alignment": 0.20}
    else:
        weights = {"astro": 0.40, "psych": 0.25, "behavior": 0.20, "alignment": 0.15}
    if not include_astro:
        weights["astro"] = 0.0
    active_total = sum(weights.values()) or 1.0
    total = (
        (astro_score * weights["astro"])
        + (psycho_score * weights["psych"])
        + (behavior_score * weights["behavior"])
        + (alignment_score * weights["alignment"])
    ) / active_total
    return _safe_norm(total)


def compute_orchestrated_matches(
    db: Session,
    *,
    user_id: str,
    mode: str,
    match_mode: str,
    candidate_ids: list[str] | None = None,
) -> list[OrchestratedMatchRow]:
    source_user = db.get(User, user_id)
    if source_user is None:
        return []

    include_astro = preference_requires_astro(source_user.matching_preference if source_user else None)

    resolved_candidate_ids = candidate_ids
    if resolved_candidate_ids is None:
        resolved_candidate_ids = [uid for uid in db.scalars(select(User.id).where(User.id != user_id)).all()]
    else:
        resolved_candidate_ids = [candidate_id for candidate_id in resolved_candidate_ids if candidate_id != user_id]
    if not resolved_candidate_ids:
        return []

    backfill_canonical_psycho_scores(db, user_ids=[user_id, *resolved_candidate_ids], dry_run=False)
    source_state = db.get(UserProfileState, user_id)
    source_psy = db.get(PsychoScore, user_id)
    source_profile = db.get(PsychProfile, user_id)
    source_astro = db.get(AstroVector, user_id)
    source_behavior = db.get(BehaviorFeature, user_id)
    if source_state is None or (source_psy is None and source_profile is None):
        return []
    if include_astro and source_astro is None:
        return []

    candidate_users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(resolved_candidate_ids))).all()}
    candidate_states = {
        row.user_id: row for row in db.scalars(select(UserProfileState).where(UserProfileState.user_id.in_(resolved_candidate_ids))).all()
    }
    candidate_psy_scores = {
        row.user_id: row for row in db.scalars(select(PsychoScore).where(PsychoScore.user_id.in_(resolved_candidate_ids))).all()
    }
    candidate_profiles = {
        row.user_id: row for row in db.scalars(select(PsychProfile).where(PsychProfile.user_id.in_(resolved_candidate_ids))).all()
    }
    candidate_behavior = {
        row.user_id: row for row in db.scalars(select(BehaviorFeature).where(BehaviorFeature.user_id.in_(resolved_candidate_ids))).all()
    }
    candidate_astros = (
        {row.user_id: row for row in db.scalars(select(AstroVector).where(AstroVector.user_id.in_(resolved_candidate_ids))).all()}
        if include_astro
        else {}
    )
    pattern_rows = db.scalars(
        select(PsychoDerivedPattern).where(PsychoDerivedPattern.user_id.in_([user_id] + resolved_candidate_ids))
    ).all()
    patterns_by_user: dict[str, list[PsychoDerivedPattern]] = defaultdict(list)
    for row in pattern_rows:
        patterns_by_user[row.user_id].append(row)

    source_matching_psych = build_matching_psych_data(
        psycho_score=source_psy,
        derived_patterns=patterns_by_user.get(user_id),
        psych_profile=source_profile,
        psych_confidence=float(source_state.psycho_confidence or 0.0),
    )
    if source_matching_psych is None:
        return []
    psycho_mul, astro_mul, behavior_mul, feedback_count = derive_feedback_weight_multipliers(db, user_id)

    rows: list[OrchestratedMatchRow] = []
    for candidate_id in resolved_candidate_ids:
        candidate_user = candidate_users.get(candidate_id)
        candidate_state = candidate_states.get(candidate_id)
        candidate_psy = candidate_psy_scores.get(candidate_id)
        candidate_profile = candidate_profiles.get(candidate_id)
        if candidate_user is None or candidate_state is None or candidate_state.stage != "eligible":
            continue

        candidate_astro = candidate_astros.get(candidate_id)
        if include_astro and candidate_astro is None:
            continue

        candidate_matching_psych = build_matching_psych_data(
            psycho_score=candidate_psy,
            derived_patterns=patterns_by_user.get(candidate_id),
            psych_profile=candidate_profile,
            psych_confidence=float(candidate_state.psycho_confidence or 0.0),
        )
        if candidate_matching_psych is None:
            continue
        dynamics = compute_compatibility_dynamics(source_matching_psych, candidate_matching_psych)
        pair = score_pair(
            p_a=source_matching_psych.vector,
            p_b=candidate_matching_psych.vector,
            u_a=source_matching_psych.uncertainty,
            u_b=candidate_matching_psych.uncertainty,
            astro_a=(source_astro.vector if source_astro else []),
            astro_b=(candidate_astro.vector if candidate_astro else []),
            behavior_a=(source_behavior.behavior_vector if source_behavior else []),
            behavior_b=(candidate_behavior.get(candidate_id).behavior_vector if candidate_behavior.get(candidate_id) else []),
            psycho_confidence=float(source_state.psycho_confidence or 0.0),
            astro_confidence=float(source_state.astro_confidence or 0.0),
            behavior_confidence=float(source_state.behavior_confidence or 0.0),
            quality_flags=source_matching_psych.quality_flags,
            include_astro=include_astro,
            dynamics=dynamics,
        )

        tuned_psy = clamp(pair.psycho_score * psycho_mul)
        tuned_astro = clamp((pair.astro_score * astro_mul) + (0.05 if mode == "friendship" and include_astro else 0.0))
        tuned_behavior = clamp(pair.behavior_score * behavior_mul)
        alignment_score = _alignment_score(source_user, candidate_user)
        tuned_final = clamp(
            _compose_total(
                astro_score=tuned_astro if include_astro else 0.0,
                psycho_score=tuned_psy,
                behavior_score=tuned_behavior,
                alignment_score=alignment_score,
                match_mode=match_mode,
                include_astro=include_astro,
            ) - dynamics.uncertainty_penalty
        )
        confidence_boost = min(0.1, feedback_count / 100.0)
        tuned_confidence = clamp(pair.confidence + confidence_boost)
        rank_score = rank_pair_score(tuned_final, tuned_confidence)

        explanation = dict(pair.explanation or {})
        explanation["confidence_note"] = dynamics.confidence_note
        explanation["public_reasons"] = list(dynamics.public_reasons)
        explanation["public_watch_items"] = list(dynamics.public_watch_items)

        dynamics_payload = {
            "attachment_compatibility": round(dynamics.attachment_compatibility, 4),
            "conflict_compatibility": round(dynamics.conflict_compatibility, 4),
            "intimacy_pace_compatibility": round(dynamics.intimacy_pace_compatibility, 4),
            "affection_compatibility": round(dynamics.affection_compatibility, 4),
            "stability_exploration_compatibility": round(dynamics.stability_exploration_compatibility, 4),
            "relational_risk_modifier": round(dynamics.relational_risk_modifier, 4),
            "uncertainty_penalty": round(dynamics.uncertainty_penalty, 4),
            "overall_dynamics_score": round(dynamics.overall_dynamics_score, 4),
            "confidence": round(dynamics.confidence, 4),
            "compatibility_score": round(tuned_final, 4),
            "ranking_score": round(rank_score, 4),
            "source_a": source_matching_psych.source if source_matching_psych else "missing",
            "source_b": candidate_matching_psych.source if candidate_matching_psych else "missing",
        }

        rows.append(
            OrchestratedMatchRow(
                other_user_id=candidate_id,
                candidate_name=candidate_user.name or candidate_id,
                candidate_city=candidate_user.birth_place.split(",")[0].strip() if candidate_user.birth_place else "Unknown",
                psycho_score=pair.psycho_score,
                astro_score=pair.astro_score,
                behavior_score=pair.behavior_score,
                compatibility_score=tuned_final,
                rank_score=rank_score,
                confidence=tuned_confidence,
                dynamics_payload=dynamics_payload,
                explanation=explanation,
                highlights=explanation_highlights(explanation),
            )
        )

    rows.sort(key=lambda row: row.rank_score, reverse=True)
    fallback_rows = [
        row for row in rows
        if row.dynamics_payload.get("source_a") == "psych_profile_fallback"
        or row.dynamics_payload.get("source_b") == "psych_profile_fallback"
    ]
    if fallback_rows:
        db.add(
            AnalyticsEvent(
                user_id=user_id,
                event_name="psychology_fallback_used",
                event_payload={
                    "match_mode": match_mode,
                    "mode": mode,
                    "fallback_match_count": len(fallback_rows),
                    "candidate_ids": [row.other_user_id for row in fallback_rows[:10]],
                },
            )
        )
    return rows


def replace_match_v2_rows(
    db: Session,
    *,
    user_id: str,
    rows: list[OrchestratedMatchRow],
    top_k: int,
) -> int:
    db.query(MatchV2).filter(MatchV2.user_id == user_id).delete()
    for row in rows[:top_k]:
        db.add(
            MatchV2(
                user_id=user_id,
                other_user_id=row.other_user_id,
                psycho_score=row.psycho_score,
                astro_score=row.astro_score,
                behavior_score=row.behavior_score,
                # compatibility_score stores the normalized compatibility read
                # before rank-facing confidence ordering is applied.
                compatibility_score=row.compatibility_score,
                # final_score remains the rank-facing score for API stability.
                final_score=row.rank_score,
                confidence=row.confidence,
                dynamics_payload=row.dynamics_payload,
                explanation=row.explanation,
            )
        )
    db.flush()
    return min(top_k, len(rows))


def replace_match_result_rows(
    db: Session,
    *,
    user_id: str,
    mode: str,
    rows: list[OrchestratedMatchRow],
) -> None:
    db.query(MatchResult).filter(MatchResult.user_id == user_id, MatchResult.mode == mode).delete()
    for row in rows:
        db.add(
            MatchResult(
                user_id=user_id,
                candidate_id=row.other_user_id,
                mode=mode,
                score=round(row.rank_score * 100, 2),
                highlights=row.highlights,
            )
        )
    db.flush()
