from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..jobs.recompute_user import recompute_matches_for_user
from ..legal_guard import require_current_consent
from ..matching_preferences import preference_requires_astro
from ..models import (
    AuthUser,
    BehaviorFeature,
    BirthData,
    NatalChart,
    OnboardingAnswer,
    PsychoItem,
    PsychoScore,
    PsychProfile,
    User,
    UserProfileState,
)
from ..security import get_current_auth_user
from ..services.assessment_flow_service import (
    build_assessment_summary_from_session,
    ingest_onboarding_responses,
    replace_derived_patterns,
)
from ..services.astro_features import compute_natal_chart_features
from ..services.eligibility import evaluate_eligibility

router = APIRouter(tags=["profile"])

CORE_PSYCHO_ITEM_IDS = {
    "B5_O_01",
    "B5_O_02",
    "B5_O_03",
    "B5_O_04",
    "B5_C_01",
    "B5_C_02",
    "B5_C_03",
    "B5_C_04",
    "B5_E_01",
    "B5_E_02",
    "B5_E_03",
    "B5_E_04",
    "B5_A_01",
    "B5_A_02",
    "B5_A_03",
    "B5_A_04",
    "B5_N_01",
    "B5_N_02",
    "B5_N_03",
    "B5_N_04",
    "ATT_01",
    "ATT_02",
    "ATT_03",
    "ATT_04",
    "CON_01",
    "CON_02",
    "CON_03",
    "VAL_01",
    "VAL_02",
    "AFF_01",
}


class OnboardingQuestion(BaseModel):
    id: str
    prompt: str
    options: list[str]


class OnboardingQuestionsResponse(BaseModel):
    ok: bool
    version: str
    questions: list[OnboardingQuestion]


class OnboardingAnswerItem(BaseModel):
    question_id: str
    value: str


class OnboardingSubmitRequest(BaseModel):
    user_id: str
    answers: list[OnboardingAnswerItem] = Field(min_length=8)


class OnboardingSubmitResponse(BaseModel):
    ok: bool
    user_id: str
    psych_profile: dict


class BirthPayload(BaseModel):
    birth_date: date
    birth_time: time
    birth_place_name: str
    lat: float
    lon: float
    timezone_iana: str
    birth_datetime_utc: str
    dst_flag: bool | None = None


class PsychoAnswersPayload(BaseModel):
    answers: dict[str, int]
    response_ms: dict[str, int] | None = None


class OnboardingSubmitV2Request(BaseModel):
    birth: BirthPayload
    psycho: PsychoAnswersPayload


QUESTIONS_V1 = [
    {
        "id": "ocean_openness",
        "prompt": "I enjoy new ideas and experiences.",
        "options": ["1", "2", "3", "4", "5"],
    },
    {
        "id": "ocean_conscientiousness",
        "prompt": "I keep routines and follow through on plans.",
        "options": ["1", "2", "3", "4", "5"],
    },
    {
        "id": "ocean_extraversion",
        "prompt": "I feel energized by social interaction.",
        "options": ["1", "2", "3", "4", "5"],
    },
    {
        "id": "ocean_agreeableness",
        "prompt": "I naturally try to keep harmony with others.",
        "options": ["1", "2", "3", "4", "5"],
    },
    {
        "id": "ocean_neuroticism",
        "prompt": "I feel stress intensely in relationships.",
        "options": ["1", "2", "3", "4", "5"],
    },
    {
        "id": "attachment_style",
        "prompt": "Closest attachment style",
        "options": ["secure", "anxious", "avoidant"],
    },
    {
        "id": "love_language",
        "prompt": "Primary love language",
        "options": ["words", "acts", "gifts", "quality_time", "touch"],
    },
    {
        "id": "communication_style",
        "prompt": "Preferred communication style",
        "options": ["direct", "gentle", "balanced"],
    },
    {
        "id": "conflict_style",
        "prompt": "Preferred conflict style",
        "options": ["collaborative", "avoidant", "assertive"],
    },
    {
        "id": "social_energy",
        "prompt": "Social energy preference",
        "options": ["introvert", "balanced", "extrovert"],
    },
    {
        "id": "novelty_preference",
        "prompt": "I seek novelty in relationships.",
        "options": ["1", "2", "3", "4", "5"],
    },
    {
        "id": "boundaries_preference",
        "prompt": "I prefer clear and explicit boundaries.",
        "options": ["1", "2", "3", "4", "5"],
    },
]


@router.get("/onboarding/questions", response_model=OnboardingQuestionsResponse)
def get_onboarding_questions():
    return {"ok": True, "version": "v1", "questions": QUESTIONS_V1}


def _scale_1_to_5(raw: str) -> float:
    try:
        value = int(raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_answer_value") from exc
    if value < 1 or value > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_answer_range")
    return (value - 1) / 4.0


@router.post("/onboarding/submit")
def submit_onboarding_v2(
    payload: OnboardingSubmitV2Request,
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    user = db.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile_not_found")

    birth_datetime_raw = payload.birth.birth_datetime_utc.replace("Z", "+00:00")
    try:
        birth_datetime_utc = datetime.fromisoformat(birth_datetime_raw).replace(tzinfo=None)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_birth_datetime_utc") from exc

    birth_row = db.get(BirthData, current_user.id)
    if not birth_row:
        birth_row = BirthData(user_id=current_user.id)
        db.add(birth_row)

    birth_row.birth_date = payload.birth.birth_date
    birth_row.birth_time = payload.birth.birth_time
    birth_row.birth_place_name = payload.birth.birth_place_name
    birth_row.lat = payload.birth.lat
    birth_row.lon = payload.birth.lon
    birth_row.timezone_iana = payload.birth.timezone_iana
    birth_row.birth_datetime_utc = birth_datetime_utc
    birth_row.dst_flag = payload.birth.dst_flag

    user.birth_date = payload.birth.birth_date.isoformat()
    user.birth_time = payload.birth.birth_time.strftime("%H:%M")
    user.birth_place = payload.birth.birth_place_name
    user.birth_latitude = payload.birth.lat
    user.birth_longitude = payload.birth.lon
    user.birth_timezone = payload.birth.timezone_iana

    items = db.query(PsychoItem).all()
    if not items:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="psycho_items_not_seeded")
    item_map = {item.id: item for item in items}
    if not CORE_PSYCHO_ITEM_IDS.issubset(item_map.keys()):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="psycho_items_incomplete")

    provided_ids = set(payload.psycho.answers.keys())
    missing_ids = sorted(CORE_PSYCHO_ITEM_IDS - provided_ids)
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"missing_psycho_items:{','.join(missing_ids)}")

    unexpected_ids = sorted(provided_ids - CORE_PSYCHO_ITEM_IDS)
    if unexpected_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unexpected_psycho_items:{','.join(unexpected_ids)}",
        )

    for item_id in sorted(CORE_PSYCHO_ITEM_IDS):
        answer = int(payload.psycho.answers[item_id])
        if answer < 1 or answer > 5:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid_answer_range:{item_id}")

    assessment_write = ingest_onboarding_responses(
        db,
        user_id=current_user.id,
        item_map=item_map,
        answers={item_id: int(payload.psycho.answers[item_id]) for item_id in sorted(CORE_PSYCHO_ITEM_IDS)},
        response_ms=payload.psycho.response_ms or {},
        assessment_mode="onboarding_v2",
        version="v2",
    )
    assessment_summary = build_assessment_summary_from_session(
        db,
        session_id=assessment_write.session.id,
        item_map=item_map,
    )
    replace_derived_patterns(db, user_id=current_user.id, derived_patterns=assessment_summary.derived_patterns)

    scored = assessment_summary.scored
    uncertainty_avg = sum(assessment_summary.legacy_uncertainty) / max(1, len(assessment_summary.legacy_uncertainty))
    psycho_completion = len(CORE_PSYCHO_ITEM_IDS) / float(len(CORE_PSYCHO_ITEM_IDS))

    psycho_row = db.get(PsychoScore, current_user.id)
    if not psycho_row:
        psycho_row = PsychoScore(user_id=current_user.id)
        db.add(psycho_row)

    psycho_row.o = assessment_summary.legacy_traits["O"]
    psycho_row.c = assessment_summary.legacy_traits["C"]
    psycho_row.e = assessment_summary.legacy_traits["E"]
    psycho_row.a = assessment_summary.legacy_traits["A"]
    psycho_row.n = assessment_summary.legacy_traits["N"]
    psycho_row.att_anxiety = assessment_summary.legacy_traits["att_anxiety"]
    psycho_row.att_avoid = assessment_summary.legacy_traits["att_avoid"]
    psycho_row.conflict_direct = assessment_summary.legacy_traits["conflict_direct"]
    psycho_row.conflict_avoid = assessment_summary.legacy_traits["conflict_avoid"]
    psycho_row.conflict_delay = assessment_summary.legacy_traits["conflict_delay"]
    psycho_row.value_stability = assessment_summary.legacy_traits["value_stability"]
    psycho_row.value_novelty = assessment_summary.legacy_traits["value_novelty"]
    psycho_row.aff_attention = assessment_summary.legacy_traits["aff_attention"]
    psycho_row.psycho_vector = assessment_summary.legacy_vector
    psycho_row.psycho_uncertainty = assessment_summary.legacy_uncertainty
    psycho_row.quality_flags = {
        **assessment_summary.scored.quality_flags,
        "assessment_session_id": assessment_summary.session.id,
        "derived_pattern_keys": [pattern.pattern_key for pattern in assessment_summary.derived_patterns],
    }
    psycho_row.computed_at = datetime.utcnow()

    astro_complete = False
    astro_confidence = 0.0
    try:
        natal = compute_natal_chart_features(
            birth_date=payload.birth.birth_date.isoformat(),
            birth_time=payload.birth.birth_time.strftime("%H:%M"),
            birth_place_name=payload.birth.birth_place_name,
            lat=payload.birth.lat,
            lon=payload.birth.lon,
            timezone_iana=payload.birth.timezone_iana,
        )
        natal_row = db.get(NatalChart, current_user.id)
        if not natal_row:
            natal_row = NatalChart(user_id=current_user.id)
            db.add(natal_row)
        natal_row.asc_sign = int(natal["asc_sign"])
        natal_row.asc_deg = float(natal["asc_deg"])
        natal_row.planets = natal["planets"]
        natal_row.aspects = natal["aspects"]
        natal_row.astro_features = natal["astro_features"]
        natal_row.astro_vector = natal["astro_vector"]
        natal_row.computed_at = natal["computed_at"]
        astro_complete = True
        astro_confidence = 1.0
    except Exception:
        astro_complete = False
        astro_confidence = 0.0

    behavior_feature = db.get(BehaviorFeature, current_user.id)
    if behavior_feature and behavior_feature.behavior_vector:
        behavior_completion = 1.0
        behavior_confidence = 0.7
    else:
        behavior_completion = 0.0
        behavior_confidence = 0.0

    state = db.get(UserProfileState, current_user.id)
    if not state:
        state = UserProfileState(user_id=current_user.id)
        db.add(state)

    eligibility = evaluate_eligibility(
        astro_completion=(1.0 if astro_complete else 0.0),
        psycho_completion=psycho_completion,
        behavior_completion=behavior_completion,
        quality_flags=assessment_summary.scored.quality_flags,
        psycho_uncertainty_avg=uncertainty_avg,
        require_astro=preference_requires_astro(user.matching_preference),
    )

    state.stage = eligibility.stage
    state.astro_complete = astro_complete
    state.psycho_complete = True
    state.required_modules_complete = eligibility.required_modules_complete
    state.quality_pass = eligibility.quality_pass
    state.astro_completion = eligibility.astro_completion
    state.psycho_completion = eligibility.psycho_completion
    state.behavior_completion = eligibility.behavior_completion
    state.astro_confidence = astro_confidence
    state.psycho_confidence = eligibility.psycho_confidence
    state.behavior_confidence = behavior_confidence
    state.overall_confidence = eligibility.overall_confidence
    state.updated_at = datetime.utcnow()

    db.commit()

    matches_recomputed = 0
    if state.stage == "eligible":
        matches_recomputed = recompute_matches_for_user(db, current_user.id, top_k=20)

    return {
        "stage": state.stage,
        "quality_pass": state.quality_pass,
        "eligibility_score": round(eligibility.eligibility_score, 4),
        "psycho_confidence": round(state.psycho_confidence, 4),
        "overall_confidence": round(state.overall_confidence, 4),
        "matches_recomputed": matches_recomputed,
        "next": "complete" if state.stage == "eligible" else "calibrating",
    }


@router.post("/onboarding/answers", response_model=OnboardingSubmitResponse)
def submit_onboarding_answers(
    payload: OnboardingSubmitRequest,
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if payload.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_user_mismatch")

    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile_not_found")

    answer_map = {item.question_id: item.value for item in payload.answers}
    required = [
        "ocean_openness",
        "ocean_conscientiousness",
        "ocean_extraversion",
        "ocean_agreeableness",
        "ocean_neuroticism",
        "attachment_style",
        "love_language",
        "communication_style",
        "conflict_style",
        "social_energy",
        "novelty_preference",
        "boundaries_preference",
    ]
    missing = [qid for qid in required if qid not in answer_map]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"missing_answers:{','.join(missing)}")

    ocean_vector = [
        _scale_1_to_5(answer_map["ocean_openness"]),
        _scale_1_to_5(answer_map["ocean_conscientiousness"]),
        _scale_1_to_5(answer_map["ocean_extraversion"]),
        _scale_1_to_5(answer_map["ocean_agreeableness"]),
        _scale_1_to_5(answer_map["ocean_neuroticism"]),
    ]
    novelty = _scale_1_to_5(answer_map["novelty_preference"])
    boundaries = _scale_1_to_5(answer_map["boundaries_preference"])

    attachment_style = answer_map["attachment_style"]
    attachment_confidence = 0.8 if attachment_style == "secure" else 0.65

    existing = db.get(PsychProfile, payload.user_id)
    if existing:
        existing.ocean_vector = ocean_vector
        existing.attachment_style = attachment_style
        existing.attachment_confidence = attachment_confidence
        existing.love_language = answer_map["love_language"]
        existing.communication_style = answer_map["communication_style"]
        existing.conflict_style = answer_map["conflict_style"]
        existing.social_energy = answer_map["social_energy"]
        existing.novelty_preference = novelty
        existing.boundaries_preference = boundaries
        existing.updated_at = datetime.utcnow()
    else:
        db.add(
            PsychProfile(
                user_id=payload.user_id,
                ocean_vector=ocean_vector,
                attachment_style=attachment_style,
                attachment_confidence=attachment_confidence,
                love_language=answer_map["love_language"],
                communication_style=answer_map["communication_style"],
                conflict_style=answer_map["conflict_style"],
                social_energy=answer_map["social_energy"],
                novelty_preference=novelty,
                boundaries_preference=boundaries,
                source_version="v1",
            )
        )

    db.query(OnboardingAnswer).filter(OnboardingAnswer.user_id == payload.user_id, OnboardingAnswer.section == "psych_v1").delete()
    for answer in payload.answers:
        db.add(
            OnboardingAnswer(
                user_id=payload.user_id,
                section="psych_v1",
                question_id=answer.question_id,
                answer={"value": answer.value},
            )
        )

    db.commit()
    return {
        "ok": True,
        "user_id": payload.user_id,
        "psych_profile": {
            "ocean_vector": ocean_vector,
            "attachment_style": attachment_style,
            "love_language": answer_map["love_language"],
            "communication_style": answer_map["communication_style"],
            "conflict_style": answer_map["conflict_style"],
            "social_energy": answer_map["social_energy"],
            "novelty_preference": novelty,
            "boundaries_preference": boundaries,
        },
    }
