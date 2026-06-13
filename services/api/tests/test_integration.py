import os
import pytest
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Configure test process env before importing app module.
os.environ["APP_ENV"] = "test"
os.environ["ADMIN_EMAILS"] = "admin@example.com"
os.environ["AUTH_RATE_LIMIT_PER_MINUTE"] = "10000"
os.environ["AUTH_REFRESH_RATE_LIMIT_PER_MINUTE"] = "10000"
os.environ["MESSAGE_SEND_RATE_LIMIT_PER_MINUTE"] = "10000"

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
import app.domains.astrology as astrology_domain  # noqa: E402
import app.domains.onboarding as onboarding_domain  # noqa: E402
from app.domains.compliance import (  # noqa: E402
    seed_default_compliance_registers,
    seed_default_policies,
    seed_default_policy_versions,
)
from app.domains.legal import seed_legal_documents  # noqa: E402
from app.jobs.seed_psycho_items import seed_psycho_items  # noqa: E402
from app.jobs.backfill_canonical_psych_scores import backfill_canonical_psycho_scores  # noqa: E402
from app.jobs.recompute_user import recompute_matches_for_user  # noqa: E402
from app.models import (  # noqa: E402
    AnalyticsEvent,
    AuthUser,
    BehaviorFeature,
    BillingProduct,
    DeletionJob,
    ExperimentAssignment,
    JobRunTelemetry,
    MatchResult,
    MatchV2,
    NatalChart,
    PsychProfile,
    PsychoAssessmentSession,
    PsychoDerivedPattern,
    PsychoItemResponse,
    PsychoReport,
    PsychoResponse,
    PsychoScore,
    TrustSafetyRisk,
    User,
    UserProfileState,
)


TEST_DB_URL = "sqlite:///./test_soulmatch.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Deterministic test stubs for astrology-heavy functions.
def fake_compute_chart(_birth):
    return {"stub": True}


def fake_chart_to_vector(_chart, dims=256):
    return [0.001] * dims


def fake_seed_candidates(_db):
    return 2


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
astrology_domain.compute_chart = fake_compute_chart
astrology_domain.chart_to_vector = fake_chart_to_vector


def fake_compute_natal_chart_features(**_kwargs):
    return {
        "asc_sign": 1,
        "asc_deg": 12.5,
        "planets": {"sun": {"sign": 1, "deg": 2.0, "house": 5, "element": "earth", "modality": "fixed"}},
        "aspects": [],
        "astro_features": {"attachment_pattern_proxy": 0.5},
        "astro_vector": [0.2] * 48,
        "computed_at": datetime.utcnow(),
    }


_DEFAULT_PSYCHO_VECTOR = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]


def set_user_eligible(user_id: str) -> None:
    with TestingSessionLocal() as db:
        row = db.get(UserProfileState, user_id)
        if not row:
            row = UserProfileState(user_id=user_id)
            db.add(row)
        row.stage = "eligible"
        row.astro_complete = True
        row.psycho_complete = True
        row.required_modules_complete = True
        row.quality_pass = True
        row.astro_completion = 1.0
        row.psycho_completion = 1.0
        row.behavior_completion = 1.0
        row.astro_confidence = 1.0
        row.psycho_confidence = 1.0
        row.behavior_confidence = 1.0
        row.overall_confidence = 1.0
        # PsychoScore is required for match computation; create a minimal record if absent.
        score = db.get(PsychoScore, user_id)
        if not score:
            db.add(PsychoScore(
                user_id=user_id,
                o=0.5, c=0.5, e=0.5, a=0.5, n=0.5,
                att_anxiety=0.5, att_avoid=0.5,
                conflict_direct=0.5, conflict_avoid=0.25, conflict_delay=0.25,
                value_stability=0.5, value_novelty=0.5,
                aff_attention=0.5,
                psycho_vector=_DEFAULT_PSYCHO_VECTOR,
                psycho_uncertainty=[0.3] * 14,
                quality_flags={},
                computed_at=datetime.utcnow(),
            ))
        db.commit()


def build_core_psycho_answers(value_cycle: list[int] | None = None) -> dict[str, int]:
    ids = [
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
    ]
    cycle = value_cycle or [2, 3, 4, 5, 1]
    return {item_id: cycle[i % len(cycle)] for i, item_id in enumerate(ids)}


def onboarding_submit_payload(answers: dict[str, int], response_ms: int = 1200) -> dict:
    return {
        "birth": {
            "birth_date": "1995-01-01",
            "birth_time": "10:30:00",
            "birth_place_name": "Toronto, Canada",
            "lat": 43.6532,
            "lon": -79.3832,
            "timezone_iana": "America/Toronto",
            "birth_datetime_utc": "1995-01-01T15:30:00Z",
            "dst_flag": False,
        },
        "psycho": {
            "answers": answers,
            "response_ms": {k: response_ms for k in answers.keys()},
        },
    }


def setup_module(_module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        seed_default_policies(db)
        seed_default_policy_versions(db)
        seed_default_compliance_registers(db)
        seed_legal_documents(db)
        seed_psycho_items(db)


def teardown_module(_module):
    Base.metadata.drop_all(bind=engine)


def signup_with_consent(client, email: str, password: str = "Strongpass123!", birth_date: str = "1990-01-01"):
    signup = client.post(
        "/auth/signup",
        json={"email": email, "password": password, "birth_date": birth_date},
    )
    if signup.status_code == 200:
        token = signup.json()["access_token"]
        consent = client.post("/legal/consent", json={"accept": True}, headers={"Authorization": f"Bearer {token}"})
        assert consent.status_code == 200
        return signup

    # Test helper is idempotent across test cases sharing a db.
    if signup.status_code == 409 and signup.json().get("detail") == "email_exists":
        admin_emails = {item.strip().lower() for item in os.getenv("ADMIN_EMAILS", "").split(",") if item.strip()}
        if email.lower() in admin_emails:
            with TestingSessionLocal() as db:
                auth_user = db.scalar(select(AuthUser).where(AuthUser.email == email))
                if auth_user and auth_user.role != "admin":
                    auth_user.role = "admin"
                    db.commit()
        login = client.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        token = login.json()["access_token"]
        consent = client.post("/legal/consent", json={"accept": True}, headers={"Authorization": f"Bearer {token}"})
        assert consent.status_code == 200
        return login

    return signup


def test_auth_signup_login_refresh_flow():
    client = TestClient(app)

    signup = signup_with_consent(client, "user1@example.com")
    assert signup.status_code == 200
    signup_body = signup.json()
    assert signup_body["access_token"]
    assert signup_body["refresh_token"]
    assert signup_body["role"] == "user"

    login = client.post(
        "/auth/login",
        json={"email": "user1@example.com", "password": "Strongpass123!"},
    )
    assert login.status_code == 200

    refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    assert refresh.status_code == 200
    assert refresh.json()["access_token"]


def test_auth_signup_age_gate():
    client = TestClient(app)
    underage = signup_with_consent(client, "young@example.com", birth_date="2012-01-01")
    assert underage.status_code == 400
    assert underage.json()["detail"] == "age_restriction_under_minimum"


def test_onboarding_and_matches_flow():
    client = TestClient(app)

    auth1 = signup_with_consent(client, "alpha@example.com").json()
    auth2 = signup_with_consent(client, "beta@example.com").json()

    user1_payload = {
        "id": auth1["user_id"],
        "name": "Alpha",
        "email": "alpha@example.com",
        "birth": {
            "date": "1995-01-01",
            "time": "10:00",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance", "friendship"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    user2_payload = {
        "id": auth2["user_id"],
        "name": "Beta",
        "email": "beta@example.com",
        "birth": {
            "date": "1996-02-02",
            "time": "11:00",
            "place": "Montreal, Canada",
            "latitude": 45.5017,
            "longitude": -73.5673,
            "timezone": "America/Toronto",
        },
        "goals": ["romance"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }

    h1 = {"Authorization": f"Bearer {auth1['access_token']}"}
    h2 = {"Authorization": f"Bearer {auth2['access_token']}"}

    assert client.post("/users", json=user1_payload, headers=h1).status_code == 200
    assert client.post("/users", json=user2_payload, headers=h2).status_code == 200

    assert client.post("/vectors/generate", json={"user_id": auth1["user_id"]}, headers=h1).status_code == 200
    assert client.post("/vectors/generate", json={"user_id": auth2["user_id"]}, headers=h2).status_code == 200
    set_user_eligible(auth1["user_id"])
    set_user_eligible(auth2["user_id"])

    match_res = client.post(
        "/matches",
        json={"user_id": auth1["user_id"], "mode": "romance"},
        headers=h1,
    )
    assert match_res.status_code == 200
    results = match_res.json()["results"]
    assert len(results) >= 1
    assert results[0]["candidate_id"] == auth2["user_id"]


def test_match_response_flags_low_supply_for_small_match_set():
    client = TestClient(app)

    auth1 = signup_with_consent(client, "low-supply-a@example.com").json()
    auth2 = signup_with_consent(client, "low-supply-b@example.com").json()

    payloads = [
        (
            auth1,
            {
                "id": auth1["user_id"],
                "name": "Low Supply A",
                "email": "low-supply-a@example.com",
                "birth": {
                    "date": "1995-01-01",
                    "time": "10:00",
                    "place": "Toronto, Canada",
                    "latitude": 43.6532,
                    "longitude": -79.3832,
                    "timezone": "America/Toronto",
                },
                "goals": ["romance"],
                "consent_privacy": True,
                "consent_sensitive_data": True,
                "policy_version": "v1",
            },
        ),
        (
            auth2,
            {
                "id": auth2["user_id"],
                "name": "Low Supply B",
                "email": "low-supply-b@example.com",
                "birth": {
                    "date": "1996-02-02",
                    "time": "11:00",
                    "place": "Montreal, Canada",
                    "latitude": 45.5017,
                    "longitude": -73.5673,
                    "timezone": "America/Toronto",
                },
                "goals": ["romance"],
                "consent_privacy": True,
                "consent_sensitive_data": True,
                "policy_version": "v1",
            },
        ),
    ]

    for auth, payload in payloads:
        headers = {"Authorization": f"Bearer {auth['access_token']}"}
        assert client.post("/users", json=payload, headers=headers).status_code == 200
        assert client.post("/vectors/generate", json={"user_id": auth["user_id"]}, headers=headers).status_code == 200
        set_user_eligible(auth["user_id"])

    headers = {"Authorization": f"Bearer {auth1['access_token']}"}
    match_res = client.post(
        "/matches",
        json={"user_id": auth1["user_id"], "mode": "romance", "candidate_ids": [auth2["user_id"]]},
        headers=headers,
    )
    assert match_res.status_code == 200
    body = match_res.json()
    assert body["low_supply"] is True
    assert len(body["results"]) == 1
    assert "smaller set" in body["message"]


def test_psych_behavior_preference_matches_without_astro_vectors():
    client = TestClient(app)

    auth1 = signup_with_consent(client, "pref-a@example.com").json()
    auth2 = signup_with_consent(client, "pref-b@example.com").json()
    h1 = {"Authorization": f"Bearer {auth1['access_token']}"}
    h2 = {"Authorization": f"Bearer {auth2['access_token']}"}

    for auth, email, name, headers in [
        (auth1, "pref-a@example.com", "Pref A", h1),
        (auth2, "pref-b@example.com", "Pref B", h2),
    ]:
        payload = {
            "id": auth["user_id"],
            "name": name,
            "email": email,
            "birth": {
                "date": "1994-04-10",
                "time": "08:15",
                "place": "Toronto, Canada",
                "latitude": 43.6532,
                "longitude": -79.3832,
                "timezone": "America/Toronto",
            },
            "goals": ["romance"],
            "matching_preference": "psych_behavior",
            "consent_privacy": True,
            "consent_sensitive_data": True,
            "policy_version": "v1",
        }
        assert client.post("/users", json=payload, headers=headers).status_code == 200

    with TestingSessionLocal() as db:
        for user_id in [auth1["user_id"], auth2["user_id"]]:
            row = db.get(UserProfileState, user_id)
            if not row:
                row = UserProfileState(user_id=user_id)
                db.add(row)
            row.stage = "eligible"
            row.astro_complete = False
            row.psycho_complete = True
            row.required_modules_complete = True
            row.quality_pass = True
            row.astro_completion = 0.0
            row.psycho_completion = 1.0
            row.behavior_completion = 1.0
            row.astro_confidence = 0.0
            row.psycho_confidence = 1.0
            row.behavior_confidence = 1.0
            row.overall_confidence = 1.0
            score = db.get(PsychoScore, user_id)
            if not score:
                db.add(PsychoScore(
                    user_id=user_id,
                    o=0.5, c=0.5, e=0.5, a=0.5, n=0.5,
                    att_anxiety=0.5, att_avoid=0.5,
                    conflict_direct=0.5, conflict_avoid=0.25, conflict_delay=0.25,
                    value_stability=0.5, value_novelty=0.5,
                    aff_attention=0.5,
                    psycho_vector=_DEFAULT_PSYCHO_VECTOR,
                    psycho_uncertainty=[0.3] * 14,
                    quality_flags={},
                    computed_at=datetime.utcnow(),
                ))
        db.commit()

    match_res = client.post(
        "/matches",
        json={"user_id": auth1["user_id"], "mode": "romance"},
        headers=h1,
    )
    assert match_res.status_code == 200
    body = match_res.json()
    assert body["ok"] is True
    assert any(item["candidate_id"] == auth2["user_id"] for item in body["results"])


def test_legacy_matches_response_flags_empty_results_with_message():
    client = TestClient(app)

    auth = signup_with_consent(client, "no-match@example.com").json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    payload = {
        "id": auth["user_id"],
        "name": "No Match",
        "email": "no-match@example.com",
        "birth": {
            "date": "1995-01-01",
            "time": "10:00",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=payload, headers=headers).status_code == 200
    assert client.post("/vectors/generate", json={"user_id": auth["user_id"]}, headers=headers).status_code == 200
    set_user_eligible(auth["user_id"])

    res = client.get(f"/matches/{auth['user_id']}", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["results"] == []
    assert body["low_supply"] is True
    assert "No strong matches are available right now" in body["message"]


def test_m2_astrology_and_psych_onboarding_flow():
    client = TestClient(app)

    auth1 = signup_with_consent(client, "m2a@example.com").json()
    auth2 = signup_with_consent(client, "m2b@example.com").json()
    h1 = {"Authorization": f"Bearer {auth1['access_token']}"}
    h2 = {"Authorization": f"Bearer {auth2['access_token']}"}

    for auth, email, name, headers in [
        (auth1, "m2a@example.com", "M2 A", h1),
        (auth2, "m2b@example.com", "M2 B", h2),
    ]:
        payload = {
            "id": auth["user_id"],
            "name": name,
            "email": email,
            "birth": {
                "date": "1997-06-20",
                "time": "09:30",
                "place": "Toronto, Canada",
                "latitude": 43.6532,
                "longitude": -79.3832,
                "timezone": "America/Toronto",
            },
            "goals": ["romance", "friendship"],
            "consent_privacy": True,
            "consent_sensitive_data": True,
            "policy_version": "v1",
        }
        assert client.post("/users", json=payload, headers=headers).status_code == 200

    questions = client.get("/onboarding/questions")
    assert questions.status_code == 200
    assert len(questions.json()["questions"]) >= 10

    answers = [
        {"question_id": "ocean_openness", "value": "4"},
        {"question_id": "ocean_conscientiousness", "value": "3"},
        {"question_id": "ocean_extraversion", "value": "5"},
        {"question_id": "ocean_agreeableness", "value": "4"},
        {"question_id": "ocean_neuroticism", "value": "2"},
        {"question_id": "attachment_style", "value": "secure"},
        {"question_id": "love_language", "value": "quality_time"},
        {"question_id": "communication_style", "value": "direct"},
        {"question_id": "conflict_style", "value": "collaborative"},
        {"question_id": "social_energy", "value": "balanced"},
        {"question_id": "novelty_preference", "value": "4"},
        {"question_id": "boundaries_preference", "value": "5"},
    ]
    onboarding = client.post("/onboarding/answers", json={"user_id": auth1["user_id"], "answers": answers}, headers=h1)
    assert onboarding.status_code == 200
    assert len(onboarding.json()["psych_profile"]["ocean_vector"]) == 5

    natal = client.post("/astrology/natal", json={"user_id": auth1["user_id"]}, headers=h1)
    assert natal.status_code == 200
    assert natal.json()["ok"] is True

    synastry = client.post(
        "/astrology/synastry",
        json={"user_id": auth1["user_id"], "target_user_id": auth2["user_id"], "mode": "romance"},
        headers=h1,
    )
    assert synastry.status_code == 200
    assert synastry.json()["ok"] is True
    assert "score" in synastry.json()


def test_m3_hybrid_match_explain_and_prediction_flow():
    client = TestClient(app)

    auth1 = signup_with_consent(client, "m3a@example.com").json()
    auth2 = signup_with_consent(client, "m3b@example.com").json()
    h1 = {"Authorization": f"Bearer {auth1['access_token']}"}
    h2 = {"Authorization": f"Bearer {auth2['access_token']}"}

    for auth, email, name, headers in [
        (auth1, "m3a@example.com", "M3 A", h1),
        (auth2, "m3b@example.com", "M3 B", h2),
    ]:
        payload = {
            "id": auth["user_id"],
            "name": name,
            "email": email,
            "birth": {
                "date": "1997-06-20",
                "time": "09:30",
                "place": "Toronto, Canada",
                "latitude": 43.6532,
                "longitude": -79.3832,
                "timezone": "America/Toronto",
            },
            "goals": ["romance", "friendship"],
            "consent_privacy": True,
            "consent_sensitive_data": True,
            "policy_version": "v1",
        }
        assert client.post("/users", json=payload, headers=headers).status_code == 200
        assert client.post("/vectors/generate", json={"user_id": auth["user_id"]}, headers=headers).status_code == 200
        set_user_eligible(auth["user_id"])

    match = client.post(
        "/matches",
        json={"user_id": auth1["user_id"], "mode": "romance", "match_mode": "attraction"},
        headers=h1,
    )
    assert match.status_code == 200
    body = match.json()
    assert body["ok"] is True
    assert body["match_mode"] == "attraction"
    assert len(body["results"]) >= 1
    candidate_id = body["results"][0]["candidate_id"]

    explain = client.get(
        f"/matches/{auth1['user_id']}/explain/{candidate_id}?mode=romance&match_mode=destiny",
        headers=h1,
    )
    assert explain.status_code == 200
    assert explain.json()["disclaimer"]
    assert len(explain.json()["reasons"]) >= 3

    prediction = client.get(
        f"/matches/{auth1['user_id']}/prediction/{candidate_id}?mode=romance&match_mode=attraction",
        headers=h1,
    )
    assert prediction.status_code == 200
    p = prediction.json()
    assert p["ok"] is True
    assert "intensity" in p and "stability" in p and "conflict_risk" in p and "growth_potential" in p


def test_m4_behavior_events_aggregation_and_profile_endpoint():
    client = TestClient(app)

    admin_auth = signup_with_consent(client, "admin@example.com").json()
    auth = signup_with_consent(client, "m4@example.com").json()
    h = {"Authorization": f"Bearer {auth['access_token']}"}
    admin_h = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    payload = {
        "id": auth["user_id"],
        "name": "M4 User",
        "email": "m4@example.com",
        "birth": {
            "date": "1997-06-20",
            "time": "09:30",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance", "friendship"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=payload, headers=h).status_code == 200

    for idx in range(6):
        event = {
            "event_name": "message_sent",
            "event_payload": {
                "reply_ms": 120000 + (idx * 1000),
                "message_length": 120 + idx,
                "asked_question": idx % 2 == 0,
                "read": True,
                "replied": idx % 3 != 0,
                "initiated": idx % 2 == 0,
                "boundary_violation": False,
            },
        }
        assert client.post("/events", json=event, headers=h).status_code == 200

    agg = client.post(
        "/admin/behavior/aggregate",
        json={"user_id": auth["user_id"], "window_days": 30},
        headers=admin_h,
    )
    assert agg.status_code == 200
    assert agg.json()["ok"] is True

    behavior = client.get("/profile/behavior", headers=h)
    assert behavior.status_code == 200
    body = behavior.json()
    assert body["ok"] is True
    assert len(body["vector"]) == 6
    assert "receptiveness_score" in body["dimensions"]

    taxonomy = client.get("/analytics/taxonomy")
    assert taxonomy.status_code == 200
    assert "message_sent" in taxonomy.json()["events"]

    funnel = client.get("/analytics/funnel?window_days=30", headers=h)
    assert funnel.status_code == 200
    f = funnel.json()
    assert f["ok"] is True
    assert len(f["steps"]) == 5

    unknown = client.post("/events", json={"event_name": "bad_event", "event_payload": {}}, headers=h)
    assert unknown.status_code == 400
    assert unknown.json()["detail"] == "unknown_event_name"


def test_experiment_assignment_is_sticky_and_logs_exposure():
    client = TestClient(app)
    auth = signup_with_consent(client, "exp@example.com").json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    profile_payload = {
        "id": auth["user_id"],
        "name": "Exp User",
        "email": "exp@example.com",
        "birth": {
            "date": "1997-06-20",
            "time": "09:30",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance", "friendship"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=profile_payload, headers=headers).status_code == 200

    first = client.post(
        "/experiments/assign",
        json={"experiment_key": "match_ranker_v1", "variants": ["control", "treatment"]},
        headers=headers,
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["ok"] is True
    assert first_body["variant"] in {"control", "treatment"}
    assert first_body["exposure_logged"] is True

    second = client.post(
        "/experiments/assign",
        json={"experiment_key": "match_ranker_v1", "variants": ["treatment", "control"]},
        headers=headers,
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["variant"] == first_body["variant"]
    assert second_body["exposure_logged"] is False

    with TestingSessionLocal() as db:
        assignments = (
            db.query(ExperimentAssignment)
            .filter(
                ExperimentAssignment.user_id == auth["user_id"],
                ExperimentAssignment.experiment_key == "match_ranker_v1",
            )
            .all()
        )
        assert len(assignments) == 1


def test_admin_analytics_retention_kpis_and_anomalies():
    client = TestClient(app)
    admin_auth = signup_with_consent(client, "admin@example.com").json()
    user_auth = signup_with_consent(client, "analytics@example.com").json()
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    user_headers = {"Authorization": f"Bearer {user_auth['access_token']}"}

    profile_payload = {
        "id": user_auth["user_id"],
        "name": "Analytics User",
        "email": "analytics@example.com",
        "birth": {
            "date": "1997-06-20",
            "time": "09:30",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance", "friendship"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=profile_payload, headers=user_headers).status_code == 200

    for event_name in ["onboarding_completed", "match_viewed", "message_sent"]:
        tracked = client.post("/events", json={"event_name": event_name, "event_payload": {}}, headers=user_headers)
        assert tracked.status_code == 200

    retention = client.get("/admin/analytics/retention?window_days=30", headers=admin_headers)
    assert retention.status_code == 200
    retention_body = retention.json()
    assert retention_body["ok"] is True
    assert "cohorts" in retention_body

    kpis = client.get("/admin/analytics/kpis?window_days=30", headers=admin_headers)
    assert kpis.status_code == 200
    kpi_body = kpis.json()
    assert kpi_body["ok"] is True
    assert "kpis" in kpi_body
    assert "match_to_message_rate" in kpi_body["kpis"]

    anomalies = client.get("/admin/analytics/anomalies?window_days=7", headers=admin_headers)
    assert anomalies.status_code == 200
    an_body = anomalies.json()
    assert an_body["ok"] is True
    assert isinstance(an_body["anomalies"], list)


def test_m5_safety_friction_and_no_risk_leak():
    client = TestClient(app)

    auth1 = signup_with_consent(client, "m5a@example.com").json()
    auth2 = signup_with_consent(client, "m5b@example.com").json()
    h1 = {"Authorization": f"Bearer {auth1['access_token']}"}
    h2 = {"Authorization": f"Bearer {auth2['access_token']}"}

    for auth, email, name, headers in [
        (auth1, "m5a@example.com", "M5 A", h1),
        (auth2, "m5b@example.com", "M5 B", h2),
    ]:
        payload = {
            "id": auth["user_id"],
            "name": name,
            "email": email,
            "birth": {
                "date": "1997-06-20",
                "time": "09:30",
                "place": "Toronto, Canada",
                "latitude": 43.6532,
                "longitude": -79.3832,
                "timezone": "America/Toronto",
            },
            "goals": ["romance", "friendship"],
            "consent_privacy": True,
            "consent_sensitive_data": True,
            "policy_version": "v1",
        }
        assert client.post("/users", json=payload, headers=headers).status_code == 200

    thread = client.post("/messages/threads", json={"other_user_id": auth2["user_id"]}, headers=h1)
    assert thread.status_code == 200
    thread_id = thread.json()["thread_id"]

    with TestingSessionLocal() as db:
        db.merge(
            TrustSafetyRisk(
                user_id=auth1["user_id"],
                risk_score=89.0,
                risk_band="critical",
                reason_codes=["SPAM_SCRIPTING"],
            )
        )
        db.commit()

    blocked = client.post(
        "/messages/send",
        json={"thread_id": thread_id, "body": "hello"},
        headers=h1,
    )
    assert blocked.status_code == 429
    assert "keep the community safe" in blocked.json()["detail"]

    tips = client.get(f"/safety/tips?target_user_id={auth1['user_id']}", headers=h2)
    assert tips.status_code == 200
    assert tips.json()["ok"] is True
    assert "risk_score" not in str(tips.json())
    assert "reason_codes" not in str(tips.json())


def test_m6_openers_timing_and_forward_only_advisor():
    client = TestClient(app)

    auth1 = signup_with_consent(client, "m6a@example.com").json()
    auth2 = signup_with_consent(client, "m6b@example.com").json()
    h1 = {"Authorization": f"Bearer {auth1['access_token']}"}
    h2 = {"Authorization": f"Bearer {auth2['access_token']}"}

    for auth, email, name, headers in [
        (auth1, "m6a@example.com", "M6 A", h1),
        (auth2, "m6b@example.com", "M6 B", h2),
    ]:
        payload = {
            "id": auth["user_id"],
            "name": name,
            "email": email,
            "birth": {
                "date": "1997-06-20",
                "time": "09:30",
                "place": "Toronto, Canada",
                "latitude": 43.6532,
                "longitude": -79.3832,
                "timezone": "America/Toronto",
            },
            "goals": ["romance", "friendship"],
            "consent_privacy": True,
            "consent_sensitive_data": True,
            "policy_version": "v1",
        }
        assert client.post("/users", json=payload, headers=headers).status_code == 200
        assert client.post("/vectors/generate", json={"user_id": auth["user_id"]}, headers=headers).status_code == 200
        set_user_eligible(auth["user_id"])

    match = client.post(
        "/matches",
        json={"user_id": auth1["user_id"], "mode": "romance", "match_mode": "attraction"},
        headers=h1,
    )
    assert match.status_code == 200
    candidate_id = match.json()["results"][0]["candidate_id"]

    openers = client.get(
        f"/matches/{auth1['user_id']}/openers/{candidate_id}?tone=playful",
        headers=h1,
    )
    assert openers.status_code == 200
    assert len(openers.json()["suggestions"]) == 5

    timing = client.get(
        f"/matches/{auth1['user_id']}/timing/{candidate_id}?mode=romance",
        headers=h1,
    )
    assert timing.status_code == 200
    assert "supportive_window" in timing.json()

    blocked = client.post(
        "/advisor",
        json={"user_id": auth1["user_id"], "prompt": "Why did my last relationship fail?"},
        headers=h1,
    )
    assert blocked.status_code == 200
    assert blocked.json()["blocked"] is True

    allowed = client.post(
        "/advisor",
        json={"user_id": auth1["user_id"], "prompt": "How can I set boundaries early with this match?"},
        headers=h1,
    )
    assert allowed.status_code == 200
    assert allowed.json()["blocked"] is False


def test_73_health_live_ready_and_jobs():
    client = TestClient(app)

    live = client.get("/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"
    assert "uptime_state" in live.json()

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] in {"ok", "degraded"}
    assert "database" in ready.json()["checks"]
    assert "startup" in ready.json()["checks"]

    with TestingSessionLocal() as db:
        db.merge(
            JobRunTelemetry(
                job_name="behavior_profiles",
                status="ok",
                run_count=3,
                success_count=3,
                failure_count=0,
            )
        )
        db.commit()

    jobs = client.get("/health/jobs")
    assert jobs.status_code == 200
    assert jobs.json()["ok"] is True
    assert isinstance(jobs.json()["jobs"], list)
    assert "error_counters" in jobs.json()


def test_admin_role_protection():
    client = TestClient(app)

    user_auth = signup_with_consent(client, "plain@example.com").json()
    admin_auth = signup_with_consent(client, "admin@example.com").json()

    user_headers = {"Authorization": f"Bearer {user_auth['access_token']}"}
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    forbidden = client.post("/admin/seed-candidates", headers=user_headers)
    assert forbidden.status_code == 403

    allowed = client.post("/admin/seed-candidates", headers=admin_headers)
    assert allowed.status_code == 200
    assert allowed.json()["ok"] is True


@pytest.mark.skip(reason="Requires Stripe integration — set STRIPE_SECRET_KEY to enable")
def test_messaging_and_billing_scaffold_flow():
    client = TestClient(app)

    auth1 = signup_with_consent(client, "msg-a@example.com").json()
    auth2 = signup_with_consent(client, "msg-b@example.com").json()
    h1 = {"Authorization": f"Bearer {auth1['access_token']}"}
    h2 = {"Authorization": f"Bearer {auth2['access_token']}"}

    for auth, email, name, headers in [
        (auth1, "msg-a@example.com", "Msg A", h1),
        (auth2, "msg-b@example.com", "Msg B", h2),
    ]:
        payload = {
            "id": auth["user_id"],
            "name": name,
            "email": email,
            "birth": {
                "date": "1997-06-20",
                "time": "09:30",
                "place": "Toronto, Canada",
                "latitude": 43.6532,
                "longitude": -79.3832,
                "timezone": "America/Toronto",
            },
            "goals": ["romance", "friendship"],
            "consent_privacy": True,
            "consent_sensitive_data": True,
            "policy_version": "v1",
        }
        assert client.post("/users", json=payload, headers=headers).status_code == 200

    thread = client.post("/messages/threads", json={"other_user_id": auth2["user_id"]}, headers=h1)
    assert thread.status_code == 200
    thread_id = thread.json()["thread_id"]

    sent = client.post("/messages/send", json={"thread_id": thread_id, "body": "hello"}, headers=h1)
    assert sent.status_code == 200
    assert sent.json()["message"]["body"] == "hello"

    listed = client.get(f"/messages/threads/{thread_id}", headers=h2)
    assert listed.status_code == 200
    assert len(listed.json()["messages"]) >= 1

    with TestingSessionLocal() as db:
        db.add(
            BillingProduct(
                code="premium_monthly",
                name="Premium Monthly",
                price_cents=1499,
                currency="USD",
                is_active=True,
            )
        )
        db.commit()

    plans = client.get("/billing/plans", headers=h1)
    assert plans.status_code == 200
    assert isinstance(plans.json()["plans"], list)

    checkout = client.post(
        "/billing/checkout-intent",
        json={"product_code": "premium_monthly", "currency": "USD"},
        headers=h1,
    )
    assert checkout.status_code == 200
    assert checkout.json()["checkout_status"] == "pending_provider_integration"




@pytest.mark.skip(reason="Requires Stripe integration — set STRIPE_SECRET_KEY to enable")
def test_billing_webhook_idempotency_and_reconciliation():
    client = TestClient(app)

    user_auth = signup_with_consent(client, "bill-user@example.com").json()
    admin_auth = signup_with_consent(client, "admin@example.com").json()
    user_headers = {"Authorization": f"Bearer {user_auth['access_token']}"}
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    with TestingSessionLocal() as db:
        existing = db.get(BillingProduct, "premium_monthly")
        if not existing:
            db.add(
                BillingProduct(
                    code="premium_monthly",
                    name="Premium Monthly",
                    price_cents=1499,
                    currency="USD",
                    is_active=True,
                )
            )
            db.commit()

    checkout = client.post(
        "/billing/checkout-intent",
        json={"product_code": "premium_monthly", "currency": "USD"},
        headers=user_headers,
    )
    assert checkout.status_code == 200
    payment_event_id = checkout.json()["payment_event_id"]

    first = client.post(
        "/billing/webhook/provider",
        json={"payment_event_id": payment_event_id, "provider_event_id": "prov-evt-1", "status": "succeeded"},
        headers=admin_headers,
    )
    assert first.status_code == 200
    assert first.json()["status"] == "succeeded"

    replay = client.post(
        "/billing/webhook/provider",
        json={"payment_event_id": payment_event_id, "provider_event_id": "prov-evt-1", "status": "succeeded"},
        headers=admin_headers,
    )
    assert replay.status_code == 200

    conflict = client.post(
        "/billing/webhook/provider",
        json={"payment_event_id": payment_event_id, "provider_event_id": "prov-evt-2", "status": "succeeded"},
        headers=admin_headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "provider_event_conflict"

    reconcile = client.get("/billing/reconciliation", headers=admin_headers)
    assert reconcile.status_code == 200
    body = reconcile.json()
    assert body["ok"] is True
    assert "summary" in body
    assert "missing_subscriptions" in body["summary"]

def test_compliance_policies_consent_rights_and_moderation_flow():
    client = TestClient(app)

    admin_auth = signup_with_consent(client, "admin@example.com").json()
    user_auth = signup_with_consent(client, "compliance@example.com").json()
    target_auth = signup_with_consent(client, "target@example.com").json()

    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    user_headers = {"Authorization": f"Bearer {user_auth['access_token']}"}

    policies = client.get("/policies")
    assert policies.status_code == 200
    assert len(policies.json()["policies"]) >= 3

    tos = client.get("/policies/terms-of-service")
    assert tos.status_code == 200
    assert tos.json()["policy_id"] == "terms-of-service"

    consent = client.post(
        "/consent",
        json={
            "policy_id": "terms-of-service",
            "policy_version": "v1",
            "consent_type": "tos",
            "granted": True,
            "locale": "en-US",
            "country": "US",
        },
        headers=user_headers,
    )
    assert consent.status_code == 200
    assert consent.json()["ok"] is True

    consent_history = client.get("/consent/history", headers=user_headers)
    assert consent_history.status_code == 200
    assert len(consent_history.json()["history"]) >= 1

    report = client.post(
        "/report",
        json={"target_user_id": target_auth["user_id"], "reason": "harassment", "details": "abusive message"},
        headers=user_headers,
    )
    assert report.status_code == 200
    report_id = report.json()["report_id"]

    block = client.post("/block", json={"blocked_user_id": target_auth["user_id"], "reason": "safety"}, headers=user_headers)
    assert block.status_code == 200

    rights_delete = client.post("/user/delete", json={"reason": "privacy request", "data": {}}, headers=user_headers)
    assert rights_delete.status_code == 200
    assert rights_delete.json()["status"] == "pending"

    rights_restrict = client.post("/user/restrict", json={"reason": "legal hold", "data": {}}, headers=user_headers)
    assert rights_restrict.status_code == 200
    assert rights_restrict.json()["status"] == "pending"

    rights_withdraw = client.post("/user/withdraw-consent", json={"reason": "withdraw", "data": {}}, headers=user_headers)
    assert rights_withdraw.status_code == 200
    assert rights_withdraw.json()["status"] == "pending"

    admin_reports = client.get("/admin/reports", headers=admin_headers)
    assert admin_reports.status_code == 200
    assert any(item["report_id"] == report_id for item in admin_reports.json()["reports"])

    suspend = client.post(
        "/admin/suspend",
        json={"user_id": target_auth["user_id"], "reason": "repeat abuse", "report_id": report_id},
        headers=admin_headers,
    )
    assert suspend.status_code == 200

    user_audit = client.get("/audit/user", headers=user_headers)
    assert user_audit.status_code == 200
    assert len(user_audit.json()["items"]) >= 1

    admin_audit = client.get("/audit/admin", headers=admin_headers)
    assert admin_audit.status_code == 200
    assert len(admin_audit.json()["items"]) >= 1


def test_delete_flow_creates_deletion_job():
    client = TestClient(app)
    auth = signup_with_consent(client, "deleteflow@example.com").json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    profile_payload = {
        "id": auth["user_id"],
        "name": "Delete Flow",
        "email": "deleteflow@example.com",
        "birth": {
            "date": "1990-01-01",
            "time": "10:00",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["friendship"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=profile_payload, headers=headers).status_code == 200

    delete_req = client.post("/rights/delete", json={"reason": "privacy", "data": {}}, headers=headers)
    assert delete_req.status_code == 200
    request_id = delete_req.json()["request_id"]

    with TestingSessionLocal() as db:
        job = db.query(DeletionJob).filter(DeletionJob.rights_request_id == request_id).first()
        assert job is not None
        assert job.status == "queued"


def test_compliance_legal_basis_retention_and_app_store_metadata():
    client = TestClient(app)
    admin_auth = signup_with_consent(client, "admin@example.com").json()
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    legal_basis = client.get("/compliance/legal-basis-map")
    assert legal_basis.status_code == 200
    assert legal_basis.json()["ok"] is True
    assert "EU" in legal_basis.json()["legal_basis_map"]

    retention = client.get("/admin/retention/rules", headers=admin_headers)
    assert retention.status_code == 200
    assert retention.json()["ok"] is True
    assert isinstance(retention.json()["rules"], list)

    metadata = client.get("/compliance/app-store")
    assert metadata.status_code == 200
    assert metadata.json()["ok"] is True
    assert metadata.json()["attorney_review_required"] is True


def test_consent_required_gate_blocks_matches_until_consent():
    client = TestClient(app)
    signup = client.post(
        "/auth/signup",
        json={"email": "gate@example.com", "password": "Strongpass123!", "birth_date": "1990-01-01"},
    )
    assert signup.status_code == 200
    token = signup.json()["access_token"]
    user_id = signup.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    blocked = client.post("/matches", json={"user_id": user_id, "mode": "romance"}, headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "current_legal_consent_required"

    consent = client.post("/legal/consent", json={"accept": True}, headers=headers)
    assert consent.status_code == 200


def test_consent_endpoint_stores_records_and_status():
    client = TestClient(app)
    auth = signup_with_consent(client, "consent-status@example.com").json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    status_res = client.get("/legal/consent/status", headers=headers)
    assert status_res.status_code == 200
    assert all(item["consented"] for item in status_res.json()["status"])


def test_export_endpoint_omits_trust_safety_score():
    client = TestClient(app)
    auth = signup_with_consent(client, "export@example.com").json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    profile_payload = {
        "id": auth["user_id"],
        "name": "Export User",
        "email": "export@example.com",
        "birth": {
            "date": "1991-01-01",
            "time": "10:00",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["friendship"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=profile_payload, headers=headers).status_code == 200

    export_res = client.get("/legal/export-data", headers=headers)
    assert export_res.status_code == 200
    body = export_res.json()
    assert "trust_safety_risk" not in body
    assert "reason_codes" not in str(body).lower()


def test_identity_gate_returns_409_for_incomplete_profile_on_match_surfaces():
    client = TestClient(app)
    auth = signup_with_consent(client, "gate409@example.com").json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    profile_payload = {
        "id": auth["user_id"],
        "name": "Gate 409",
        "email": "gate409@example.com",
        "birth": {
            "date": "1993-02-01",
            "time": "09:00",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=profile_payload, headers=headers).status_code == 200

    res_post = client.post("/matches", json={"user_id": auth["user_id"], "mode": "romance"}, headers=headers)
    assert res_post.status_code == 409
    assert res_post.json()["detail"] == "profile_incomplete"

    res_get_v2 = client.get("/matches", headers=headers)
    assert res_get_v2.status_code == 409
    assert res_get_v2.json()["detail"] == "profile_incomplete"

    res_get_legacy = client.get(f"/matches/{auth['user_id']}", headers=headers)
    assert res_get_legacy.status_code == 409
    assert res_get_legacy.json()["detail"] == "profile_incomplete"


def test_onboarding_submit_rejects_invalid_psycho_payload():
    onboarding_domain.compute_natal_chart_features = fake_compute_natal_chart_features
    client = TestClient(app)
    auth = signup_with_consent(client, "invalid-psy@example.com").json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    profile_payload = {
        "id": auth["user_id"],
        "name": "Invalid Psycho",
        "email": "invalid-psy@example.com",
        "birth": {
            "date": "1993-02-01",
            "time": "09:00",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=profile_payload, headers=headers).status_code == 200

    missing_answers = build_core_psycho_answers()
    missing_answers.pop("AFF_01")
    missing = client.post(
        "/onboarding/submit",
        json=onboarding_submit_payload(missing_answers),
        headers=headers,
    )
    assert missing.status_code == 400
    assert missing.json()["detail"].startswith("missing_psycho_items:")

    invalid_answers = build_core_psycho_answers()
    invalid_answers["B5_O_01"] = 7
    invalid = client.post(
        "/onboarding/submit",
        json=onboarding_submit_payload(invalid_answers),
        headers=headers,
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"].startswith("invalid_answer_range:")


def test_onboarding_stage_transitions_incomplete_calibrating_eligible(monkeypatch):
    client = TestClient(app)
    auth = signup_with_consent(client, "stageflow@example.com").json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    profile_payload = {
        "id": auth["user_id"],
        "name": "Stage Flow",
        "email": "stageflow@example.com",
        "birth": {
            "date": "1993-02-01",
            "time": "09:00",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=profile_payload, headers=headers).status_code == 200

    def fail_astro(**_kwargs):
        raise ValueError("forced_astro_failure")

    monkeypatch.setattr(onboarding_domain, "compute_natal_chart_features", fail_astro)
    first = client.post(
        "/onboarding/submit",
        json=onboarding_submit_payload(build_core_psycho_answers(), response_ms=1200),
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["stage"] == "incomplete"

    monkeypatch.setattr(onboarding_domain, "compute_natal_chart_features", fake_compute_natal_chart_features)
    straight_answers = {key: 5 for key in build_core_psycho_answers().keys()}
    second = client.post(
        "/onboarding/submit",
        json=onboarding_submit_payload(straight_answers, response_ms=100),
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["stage"] == "calibrating"

    third = client.post(
        "/onboarding/submit",
        json=onboarding_submit_payload(build_core_psycho_answers([1, 2, 3, 4, 5]), response_ms=1400),
        headers=headers,
    )
    assert third.status_code == 200
    assert third.json()["stage"] == "eligible"


def test_onboarding_submit_writes_canonical_sessions_responses_and_patterns():
    onboarding_domain.compute_natal_chart_features = fake_compute_natal_chart_features
    client = TestClient(app)
    auth = signup_with_consent(client, "dualwrite@example.com").json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    user_id = auth["user_id"]

    profile_payload = {
        "id": user_id,
        "name": "Dual Write",
        "email": "dualwrite@example.com",
        "birth": {
            "date": "1993-02-01",
            "time": "09:00",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=profile_payload, headers=headers).status_code == 200

    response = client.post(
        "/onboarding/submit",
        json=onboarding_submit_payload(build_core_psycho_answers([1, 2, 3, 4, 5]), response_ms=1250),
        headers=headers,
    )
    assert response.status_code == 200

    with TestingSessionLocal() as db:
        legacy_rows = db.query(PsychoResponse).filter(PsychoResponse.user_id == user_id).all()
        session_rows = db.query(PsychoAssessmentSession).filter(PsychoAssessmentSession.user_id == user_id).all()
        pattern_rows = db.query(PsychoDerivedPattern).filter(PsychoDerivedPattern.user_id == user_id).all()
        psycho_row = db.get(PsychoScore, user_id)

        assert len(legacy_rows) == 0
        assert len(session_rows) == 1
        assert session_rows[0].status == "completed"

        item_response_rows = (
            db.query(PsychoItemResponse)
            .filter(PsychoItemResponse.session_id == session_rows[0].id)
            .all()
        )
        assert len(item_response_rows) == len(build_core_psycho_answers())
        assert all(row.response_time_ms == 1250 for row in item_response_rows)

        assert len(pattern_rows) == 5
        assert psycho_row is not None
        assert len(psycho_row.psycho_vector) == 14
        assert len(psycho_row.psycho_uncertainty) == 14
        assert psycho_row.quality_flags["assessment_session_id"] == session_rows[0].id
        assert len(psycho_row.quality_flags["derived_pattern_keys"]) == 5


def test_public_psychology_assessment_flow_and_report_privacy():
    client = TestClient(app)
    auth = signup_with_consent(client, "psych-public@example.com").json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    user_id = auth["user_id"]

    profile_payload = {
        "id": user_id,
        "name": "Psych Public",
        "email": "psych-public@example.com",
        "birth": {
            "date": "1993-02-01",
            "time": "09:00",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=profile_payload, headers=headers).status_code == 200

    start = client.post("/psychology/assessment/start", headers=headers)
    assert start.status_code == 200
    start_body = start.json()
    assert start_body["session_id"]
    assert start_body["assessment_mode"] == "standard"
    assert start_body["first_item"]["id"]
    assert start_body["progress"]["step_index"] == 1
    assert start_body["progress"]["estimated_total_steps"] >= 1
    assert start_body["progress"]["is_followup"] is False
    assert start_body["progress"]["session_status"] in {"started", "in_progress"}

    current_item_id = start_body["first_item"]["id"]
    completion_status = "in_progress"
    for idx in range(5):
        answer = client.post(
            "/psychology/assessment/answer",
            json={
                "session_id": start_body["session_id"],
                "item_id": current_item_id,
                "answer_value": 4 if idx == 0 else 3,
                "first_answer_value": 4 if idx == 0 else 3,
                "considered_answer_value": 4 if idx == 0 else 3,
                "response_time_ms": 1800,
                "changed_answer_count": 0,
                "returned_to_question": False,
                "skipped": False,
            },
            headers=headers,
        )
        assert answer.status_code == 200
        assert answer.json()["ok"] is True
        assert "progress" in answer.json()
        assert "remaining_steps_hint" in answer.json()["progress"]

        complete = client.post(
            "/psychology/assessment/complete",
            json={"session_id": start_body["session_id"]},
            headers=headers,
        )
        assert complete.status_code == 200
        complete_body = complete.json()
        completion_status = complete_body["completion_status"]
        if completion_status == "completed":
            break
        assert completion_status == "awaiting_followup"
        assert complete_body["next_item"] is not None
        assert complete_body["progress"]["is_followup"] is True
        assert complete_body["progress"]["phase"] == "clarification"
        current_item_id = complete_body["next_item"]["id"]

    assert completion_status == "completed"
    assert complete_body["report_available"] is True
    assert complete_body["progress"]["session_status"] == "completed"
    assert complete_body["progress"]["progress_ratio"] == 1.0

    report = client.get("/psychology/report/me", headers=headers)
    assert report.status_code == 200
    report_body = report.json()
    assert report_body["session_id"] == start_body["session_id"]
    assert "personality_summary" in report_body
    assert "confidence_summary" in report_body
    assert "psycho_vector" not in report_body
    assert "psycho_uncertainty" not in report_body
    assert "traits" not in report_body
    assert "contradiction_score" not in report_body
    assert "quality_flags" not in report_body

    history = client.get("/psychology/report/history", headers=headers)
    assert history.status_code == 200
    history_body = history.json()
    assert len(history_body["reports"]) == 1
    assert history_body["reports"][0]["is_current"] is True
    assert history_body["reports"][0]["session_id"] == start_body["session_id"]
    assert "traits" not in history_body["reports"][0]
    assert "psycho_vector" not in history_body["reports"][0]

    with TestingSessionLocal() as db:
        session_rows = db.query(PsychoAssessmentSession).filter(PsychoAssessmentSession.user_id == user_id).all()
        assert len(session_rows) == 1
        assert session_rows[0].status == "completed"
        assert db.query(PsychoItemResponse).filter(PsychoItemResponse.session_id == session_rows[0].id).count() >= 1
        assert db.query(PsychoResponse).filter(PsychoResponse.user_id == user_id).count() == 0
        assert db.query(PsychoDerivedPattern).filter(PsychoDerivedPattern.user_id == user_id).count() == 5
        assert db.query(PsychoReport).filter(PsychoReport.user_id == user_id).count() == 1
        latest_report = db.query(PsychoReport).filter(PsychoReport.user_id == user_id).first()
        assert latest_report is not None
        assert latest_report.session_id == session_rows[0].id
        event_names = {row.event_name for row in db.query(AnalyticsEvent).filter(AnalyticsEvent.user_id == user_id).all()}
        assert "psychology_assessment_completed" in event_names
        assert "psychology_report_generated" in event_names
        assert "psychology_profile_updated" in event_names
        assert "psychology_compatibility_refresh_requested" in event_names
        state = db.get(UserProfileState, user_id)
        assert state is not None
        assert state.psycho_complete is True
        assert state.psycho_completion == 1.0
        assert state.psycho_confidence > 0


def test_public_psychology_routes_require_auth_and_report_is_self_only():
    client = TestClient(app)
    unauthorized = client.get("/psychology/report/me")
    assert unauthorized.status_code in {401, 403}
    unauthorized_history = client.get("/psychology/report/history")
    assert unauthorized_history.status_code in {401, 403}

    auth_a = signup_with_consent(client, "psych-a@example.com").json()
    headers_a = {"Authorization": f"Bearer {auth_a['access_token']}"}
    auth_b = signup_with_consent(client, "psych-b@example.com").json()
    headers_b = {"Authorization": f"Bearer {auth_b['access_token']}"}

    profile_payload_a = {
        "id": auth_a["user_id"],
        "name": "Psych A",
        "email": "psych-a@example.com",
        "birth": {
            "date": "1993-02-01",
            "time": "09:00",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=profile_payload_a, headers=headers_a).status_code == 200

    start = client.post("/psychology/assessment/start", headers=headers_a)
    session_id = start.json()["session_id"]
    item_id = start.json()["first_item"]["id"]
    for _ in range(4):
        client.post(
            "/psychology/assessment/answer",
            json={"session_id": session_id, "item_id": item_id, "answer_value": 3},
            headers=headers_a,
        )
        complete = client.post("/psychology/assessment/complete", json={"session_id": session_id}, headers=headers_a)
        assert complete.status_code == 200
        if complete.json()["completion_status"] == "completed":
            break
        item_id = complete.json()["next_item"]["id"]

    report_other_user = client.get("/psychology/report/me", headers=headers_b)
    assert report_other_user.status_code == 404


def test_public_psychology_reports_are_versioned_and_latest_report_is_returned():
    client = TestClient(app)
    auth = signup_with_consent(client, "psych-versioned@example.com").json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    user_id = auth["user_id"]

    profile_payload = {
        "id": user_id,
        "name": "Psych Versioned",
        "email": "psych-versioned@example.com",
        "birth": {
            "date": "1993-02-01",
            "time": "09:00",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=profile_payload, headers=headers).status_code == 200

    latest_version = None
    for score in (5, 2):
        start = client.post("/psychology/assessment/start", headers=headers)
        session_id = start.json()["session_id"]
        item_id = start.json()["first_item"]["id"]
        for _ in range(4):
            client.post(
                "/psychology/assessment/answer",
                json={"session_id": session_id, "item_id": item_id, "answer_value": score},
                headers=headers,
            )
            complete = client.post("/psychology/assessment/complete", json={"session_id": session_id}, headers=headers)
            body = complete.json()
            if body["completion_status"] == "completed":
                break
            item_id = body["next_item"]["id"]
        latest = client.get("/psychology/report/me", headers=headers)
        assert latest.status_code == 200
        latest_version = latest.json()["report_version"]

    history = client.get("/psychology/report/history", headers=headers)
    assert history.status_code == 200
    history_body = history.json()
    assert [report["report_version"] for report in history_body["reports"]] == ["r2", "r1"]
    assert history_body["reports"][0]["is_current"] is True
    assert history_body["reports"][1]["is_current"] is False

    with TestingSessionLocal() as db:
        reports = (
            db.query(PsychoReport)
            .filter(PsychoReport.user_id == user_id)
            .order_by(PsychoReport.created_at.asc(), PsychoReport.id.asc())
            .all()
        )
        assert len(reports) == 2
        assert reports[0].report_version == "r1"
        assert reports[1].report_version == "r2"
        assert reports[0].session_id is not None
        assert reports[1].session_id is not None
        assert latest_version == "r2"


def test_matches_v2_returns_top_7_high_certainty():
    client = TestClient(app)
    auth = signup_with_consent(client, "top7@example.com").json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    user_id = auth["user_id"]

    profile_payload = {
        "id": user_id,
        "name": "Top Seven",
        "email": "top7@example.com",
        "birth": {
            "date": "1993-02-01",
            "time": "09:00",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=profile_payload, headers=headers).status_code == 200

    with TestingSessionLocal() as db:
        state = db.get(UserProfileState, user_id)
        if not state:
            state = UserProfileState(user_id=user_id)
            db.add(state)
        state.stage = "eligible"
        state.required_modules_complete = True
        state.quality_pass = True
        state.astro_complete = True
        state.psycho_complete = True
        state.astro_completion = 1.0
        state.psycho_completion = 1.0
        state.behavior_completion = 1.0
        state.astro_confidence = 1.0
        state.psycho_confidence = 1.0
        state.behavior_confidence = 1.0
        state.overall_confidence = 1.0

        for idx in range(10):
            other_id = f"top7-cand-{idx}"
            db.merge(
                User(
                    id=other_id,
                    name=f"Candidate {idx}",
                    email=None,
                    birth_date="1990-01-01",
                    birth_time="10:00",
                    birth_place="Toronto, Canada",
                    goals=["romance"],
                    status="active",
                )
            )
            db.merge(
                MatchV2(
                    user_id=user_id,
                    other_user_id=other_id,
                    psycho_score=0.6 + (idx * 0.01),
                    astro_score=0.6 + (idx * 0.01),
                    behavior_score=0.6 + (idx * 0.01),
                    final_score=0.99 - (idx * 0.02),
                    confidence=0.85 - (idx * 0.01),
                    explanation={"top_drivers": [], "confidence": 0.8},
                )
            )
        db.commit()

    result = client.get("/matches", headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert len(body) == 7
    scores = [item["final_score"] for item in body]
    assert scores == sorted(scores, reverse=True)


def test_recompute_matches_uses_dynamics_confidence_and_safe_explanations():
    client = TestClient(app)
    auth = signup_with_consent(client, "dyn-source@example.com").json()
    source_headers = {"Authorization": f"Bearer {auth['access_token']}"}
    user_id = auth["user_id"]

    profile_payload = {
        "id": user_id,
        "name": "Dynamics Source",
        "email": "dyn-source@example.com",
        "birth": {
            "date": "1993-02-01",
            "time": "09:00",
            "place": "Toronto, Canada",
            "latitude": 43.6532,
            "longitude": -79.3832,
            "timezone": "America/Toronto",
        },
        "goals": ["romance"],
        "consent_privacy": True,
        "consent_sensitive_data": True,
        "policy_version": "v1",
    }
    assert client.post("/users", json=profile_payload, headers=source_headers).status_code == 200

    candidate_ids: list[str] = []
    for idx in range(2):
        other_auth = signup_with_consent(client, f"dyn-cand-{idx}@example.com").json()
        headers = {"Authorization": f"Bearer {other_auth['access_token']}"}
        candidate_ids.append(other_auth["user_id"])
        payload = {
            "id": other_auth["user_id"],
            "name": f"Candidate {idx}",
            "email": f"dyn-cand-{idx}@example.com",
            "birth": {
                "date": "1994-03-01",
                "time": "08:00",
                "place": "Montreal, Canada",
                "latitude": 45.5017,
                "longitude": -73.5673,
                "timezone": "America/Toronto",
            },
            "goals": ["romance"],
            "consent_privacy": True,
            "consent_sensitive_data": True,
            "policy_version": "v1",
        }
        assert client.post("/users", json=payload, headers=headers).status_code == 200

    with TestingSessionLocal() as db:
        all_ids = [user_id] + candidate_ids
        for idx, uid in enumerate(all_ids):
            user = db.get(User, uid)
            user.matching_preference = "psych_behavior"
            state = db.get(UserProfileState, uid)
            if not state:
                state = UserProfileState(user_id=uid)
                db.add(state)
            state.stage = "eligible"
            state.required_modules_complete = True
            state.quality_pass = True
            state.astro_complete = False
            state.psycho_complete = True
            state.astro_completion = 0.0
            state.psycho_completion = 1.0
            state.behavior_completion = 1.0
            state.astro_confidence = 0.0
            state.behavior_confidence = 0.85
            state.overall_confidence = 0.8
            state.psycho_confidence = 0.86 if idx == 0 else (0.82 if idx == 1 else 0.38)

        scores = {
            user_id: PsychoScore(
                user_id=user_id,
                o=0.62,
                c=0.58,
                e=0.55,
                a=0.64,
                n=0.38,
                att_anxiety=0.34,
                att_avoid=0.28,
                reassurance_need=0.6,
                independence_need=0.4,
                vulnerability_comfort=0.7,
                conflict_direct=0.73,
                conflict_avoid=0.24,
                conflict_delay=0.25,
                emotional_regulation=0.76,
                value_stability=0.57,
                value_novelty=0.43,
                aff_attention=0.74,
                aff_touch=0.62,
                aff_words=0.71,
                aff_acts=0.58,
                aff_gifts=0.35,
                psycho_vector=[0.62, 0.58, 0.55, 0.64, 0.38, 0.34, 0.28, 0.73, 0.24, 0.25, 0.57, 0.43, 0.74, 0.5],
                psycho_uncertainty=[0.12] * 14,
                quality_flags={"canonical_dimension_version": "v2"},
            ),
            candidate_ids[0]: PsychoScore(
                user_id=candidate_ids[0],
                o=0.61,
                c=0.57,
                e=0.52,
                a=0.62,
                n=0.4,
                att_anxiety=0.36,
                att_avoid=0.3,
                reassurance_need=0.58,
                independence_need=0.42,
                vulnerability_comfort=0.68,
                conflict_direct=0.71,
                conflict_avoid=0.22,
                conflict_delay=0.28,
                emotional_regulation=0.74,
                value_stability=0.55,
                value_novelty=0.45,
                aff_attention=0.7,
                aff_touch=0.6,
                aff_words=0.69,
                aff_acts=0.57,
                aff_gifts=0.34,
                psycho_vector=[0.61, 0.57, 0.52, 0.62, 0.4, 0.36, 0.3, 0.71, 0.22, 0.28, 0.55, 0.45, 0.7, 0.5],
                psycho_uncertainty=[0.14] * 14,
                quality_flags={"canonical_dimension_version": "v2"},
            ),
            candidate_ids[1]: PsychoScore(
                user_id=candidate_ids[1],
                o=0.6,
                c=0.55,
                e=0.5,
                a=0.58,
                n=0.62,
                att_anxiety=0.78,
                att_avoid=0.72,
                reassurance_need=0.8,
                independence_need=0.74,
                vulnerability_comfort=0.28,
                conflict_direct=0.31,
                conflict_avoid=0.77,
                conflict_delay=0.74,
                emotional_regulation=0.3,
                value_stability=0.3,
                value_novelty=0.7,
                aff_attention=0.4,
                aff_touch=0.32,
                aff_words=0.35,
                aff_acts=0.38,
                aff_gifts=0.7,
                psycho_vector=[0.6, 0.55, 0.5, 0.58, 0.62, 0.78, 0.72, 0.31, 0.77, 0.74, 0.3, 0.7, 0.4, 0.5],
                psycho_uncertainty=[0.46] * 14,
                quality_flags={"canonical_dimension_version": "v2", "straight_lining": True},
            ),
        }
        for row in scores.values():
            db.merge(row)

        db.merge(PsychProfile(user_id=user_id, love_language="quality_time", communication_style="direct", conflict_style="collaborative", attachment_style="secure", novelty_preference=0.43, boundaries_preference=0.38))
        db.merge(PsychProfile(user_id=candidate_ids[0], love_language="quality_time", communication_style="direct", conflict_style="collaborative", attachment_style="secure", novelty_preference=0.45, boundaries_preference=0.4))
        db.merge(PsychProfile(user_id=candidate_ids[1], love_language="gifts", communication_style="guarded", conflict_style="avoidant", attachment_style="anxious", novelty_preference=0.76, boundaries_preference=0.7))

        for uid in all_ids:
            db.merge(
                BehaviorFeature(
                    user_id=uid,
                    response_consistency=0.7,
                    response_delay_var=0.3,
                    initiative_ratio=0.5,
                    conversation_balance=0.55,
                    engagement_stability=0.68,
                    boundary_respect=0.82,
                    emotional_variability=0.4,
                    behavior_vector=[0.68, 0.72, 0.48, 0.56, 0.69, 0.81] if uid != candidate_ids[1] else [0.4, 0.35, 0.7, 0.42, 0.45, 0.6],
                    behavior_uncertainty=[0.2] * 6,
                )
            )

        pattern_rows = [
            (user_id, "relational_security_profile", 0.74, 0.82),
            (user_id, "conflict_repair_style", 0.76, 0.8),
            (user_id, "intimacy_pace", 0.66, 0.79),
            (user_id, "stability_vs_exploration_profile", 0.45, 0.78),
            (user_id, "emotional_reactivity_profile", 0.32, 0.8),
            (candidate_ids[0], "relational_security_profile", 0.72, 0.8),
            (candidate_ids[0], "conflict_repair_style", 0.73, 0.79),
            (candidate_ids[0], "intimacy_pace", 0.63, 0.78),
            (candidate_ids[0], "stability_vs_exploration_profile", 0.48, 0.77),
            (candidate_ids[0], "emotional_reactivity_profile", 0.35, 0.79),
            (candidate_ids[1], "relational_security_profile", 0.28, 0.45),
            (candidate_ids[1], "conflict_repair_style", 0.24, 0.4),
            (candidate_ids[1], "intimacy_pace", 0.22, 0.42),
            (candidate_ids[1], "stability_vs_exploration_profile", 0.76, 0.5),
            (candidate_ids[1], "emotional_reactivity_profile", 0.82, 0.52),
        ]
        for uid, key, score, confidence in pattern_rows:
            db.add(
                PsychoDerivedPattern(
                    user_id=uid,
                    pattern_key=key,
                    pattern_score=score,
                    confidence=confidence,
                    contributing_dimensions={},
                    explanation_internal="internal",
                )
            )

        db.commit()
        created = recompute_matches_for_user(db, user_id, top_k=5)
        assert created >= 2

        rows = db.query(MatchV2).filter(MatchV2.user_id == user_id).order_by(MatchV2.final_score.desc()).all()
        assert rows[0].other_user_id == candidate_ids[0]
        assert rows[0].confidence > rows[1].confidence
        assert rows[0].explanation["public_reasons"]
        assert rows[0].dynamics_payload["source_a"] == "canonical"
        assert rows[0].dynamics_payload["source_b"] == "canonical"
        assert "att_anxiety" not in str(rows[0].explanation)
        assert "contradiction" not in str(rows[0].explanation).lower()

        db.add(
            MatchResult(
                user_id=user_id,
                candidate_id=candidate_ids[0],
                mode="romance",
                score=round(rows[0].final_score * 100, 2),
                highlights=["seed"],
            )
        )
        db.commit()

    matches_res = client.get("/matches", headers=source_headers)
    assert matches_res.status_code == 200
    body = matches_res.json()
    assert body[0]["other_user_id"] == candidate_ids[0]
    assert "att_anxiety" not in str(body[0]["explanation"])
    assert "diagnosis" not in str(body[0]["explanation"]).lower()

    post_matches = client.post(
        "/matches",
        json={"user_id": user_id, "mode": "romance", "match_mode": "destiny", "candidate_ids": candidate_ids},
        headers=source_headers,
    )
    assert post_matches.status_code == 200
    post_body = post_matches.json()
    assert post_body["results"][0]["candidate_id"] == body[0]["other_user_id"]
    assert post_body["results"][0]["highlights"]
    assert "att_anxiety" not in str(post_body["results"][0]["highlights"])

    explain_res = client.get(
        f"/matches/{user_id}/explain/{candidate_ids[0]}?mode=romance&match_mode=destiny",
        headers=source_headers,
    )
    assert explain_res.status_code == 200
    explain_body = explain_res.json()
    assert len(explain_body["reasons"]) >= 2
    assert all("att_anxiety" not in reason for reason in explain_body["reasons"])
    assert all("avoidant" not in reason.lower() for reason in explain_body["reasons"])

    prediction_res = client.get(
        f"/matches/{user_id}/prediction/{candidate_ids[0]}?mode=romance&match_mode=attraction",
        headers=source_headers,
    )
    assert prediction_res.status_code == 200
    prediction_body = prediction_res.json()
    assert prediction_body["growth_potential"] >= prediction_body["conflict_risk"]


def test_canonical_backfill_updates_partial_rows_and_preserves_rank_vs_compatibility_scores():
    with TestingSessionLocal() as db:
        for user_id in ("usr-backfill-source", "usr-backfill-candidate"):
            db.merge(
                User(
                    id=user_id,
                    name=user_id,
                    email=f"{user_id}@example.com",
                    birth_date="1990-01-01",
                    birth_time="10:00",
                    birth_place="Toronto, Canada",
                    goals=["romance"],
                    matching_preference="psych_behavior",
                    status="active",
                    created_at=datetime.utcnow(),
                )
            )
            db.merge(
                UserProfileState(
                    user_id=user_id,
                    stage="eligible",
                    psycho_complete=True,
                    required_modules_complete=True,
                    quality_pass=True,
                    psycho_completion=1.0,
                    behavior_completion=1.0,
                    psycho_confidence=0.75,
                    behavior_confidence=0.8,
                    overall_confidence=0.78,
                )
            )

        db.merge(
            PsychoScore(
                user_id="usr-backfill-source",
                o=0.6,
                c=0.58,
                e=0.52,
                a=0.64,
                n=0.4,
                att_anxiety=0.35,
                att_avoid=0.31,
                conflict_direct=0.7,
                conflict_avoid=0.25,
                conflict_delay=0.3,
                value_stability=0.55,
                value_novelty=0.45,
                aff_attention=0.72,
                psycho_vector=[0.6, 0.58, 0.52, 0.64, 0.4, 0.35, 0.31, 0.7, 0.25, 0.3, 0.55, 0.45, 0.72, 0.5],
                psycho_uncertainty=[0.2] * 14,
                quality_flags={},
            )
        )
        db.merge(
            PsychoScore(
                user_id="usr-backfill-candidate",
                o=0.61,
                c=0.57,
                e=0.53,
                a=0.62,
                n=0.39,
                att_anxiety=0.34,
                att_avoid=0.29,
                reassurance_need=0.56,
                independence_need=0.41,
                vulnerability_comfort=0.67,
                conflict_direct=0.71,
                conflict_avoid=0.23,
                conflict_delay=0.27,
                emotional_regulation=0.75,
                value_stability=0.54,
                value_novelty=0.46,
                aff_attention=0.71,
                aff_touch=0.61,
                aff_words=0.68,
                aff_acts=0.56,
                aff_gifts=0.33,
                psycho_vector=[0.61, 0.57, 0.53, 0.62, 0.39, 0.34, 0.29, 0.71, 0.23, 0.27, 0.54, 0.46, 0.71, 0.5],
                psycho_uncertainty=[0.14] * 14,
                quality_flags={"canonical_dimension_version": "v2"},
            )
        )
        db.merge(
            PsychProfile(
                user_id="usr-backfill-source",
                love_language="gifts",
                communication_style="direct",
                conflict_style="collaborative",
                attachment_style="secure",
                novelty_preference=0.45,
                boundaries_preference=0.74,
            )
        )
        db.merge(
            BehaviorFeature(
                user_id="usr-backfill-source",
                response_consistency=0.7,
                response_delay_var=0.3,
                initiative_ratio=0.5,
                conversation_balance=0.55,
                engagement_stability=0.68,
                boundary_respect=0.82,
                emotional_variability=0.4,
                behavior_vector=[0.68, 0.72, 0.48, 0.56, 0.69, 0.81],
                behavior_uncertainty=[0.2] * 6,
            )
        )
        db.merge(
            BehaviorFeature(
                user_id="usr-backfill-candidate",
                response_consistency=0.71,
                response_delay_var=0.31,
                initiative_ratio=0.49,
                conversation_balance=0.57,
                engagement_stability=0.69,
                boundary_respect=0.81,
                emotional_variability=0.39,
                behavior_vector=[0.67, 0.71, 0.5, 0.57, 0.68, 0.8],
                behavior_uncertainty=[0.2] * 6,
            )
        )
        db.commit()

        results = backfill_canonical_psycho_scores(db, user_ids=["usr-backfill-source"])
        db.commit()
        assert results[0].canonical_dimension_version == "v2_partial"

        created = recompute_matches_for_user(db, "usr-backfill-source", top_k=5)
        assert created >= 1

        source_score = db.get(PsychoScore, "usr-backfill-source")
        row = db.query(MatchV2).filter(MatchV2.user_id == "usr-backfill-source").first()
        assert source_score is not None
        assert source_score.quality_flags["canonical_dimension_version"] == "v2_partial"
        assert "independence_need" in source_score.quality_flags["canonical_dimensions"]
        assert "aff_gifts" in source_score.quality_flags["canonical_dimensions"]
        assert row is not None
        assert row.compatibility_score != row.final_score
        assert row.dynamics_payload["source_a"] == "canonical_partial"


def test_recompute_matches_supports_profile_only_fallback_users():
    with TestingSessionLocal() as db:
        for user_id in ("usr-fallback-source", "usr-fallback-candidate"):
            db.merge(
                User(
                    id=user_id,
                    name=user_id,
                    email=f"{user_id}@example.com",
                    birth_date="1990-01-01",
                    birth_time="10:00",
                    birth_place="Toronto, Canada",
                    goals=["romance"],
                    matching_preference="psych_behavior",
                    status="active",
                    created_at=datetime.utcnow(),
                )
            )
            db.merge(
                UserProfileState(
                    user_id=user_id,
                    stage="eligible",
                    psycho_complete=True,
                    required_modules_complete=True,
                    quality_pass=True,
                    psycho_completion=1.0,
                    behavior_completion=1.0,
                    psycho_confidence=0.62,
                    behavior_confidence=0.76,
                    overall_confidence=0.7,
                )
            )
            db.merge(
                PsychProfile(
                    user_id=user_id,
                    ocean_vector=[0.6, 0.58, 0.52, 0.64, 0.4],
                    love_language="quality_time",
                    communication_style="direct",
                    conflict_style="collaborative",
                    attachment_style="secure",
                    novelty_preference=0.45,
                    boundaries_preference=0.42,
                )
            )
            db.merge(
                BehaviorFeature(
                    user_id=user_id,
                    response_consistency=0.7,
                    response_delay_var=0.3,
                    initiative_ratio=0.5,
                    conversation_balance=0.55,
                    engagement_stability=0.68,
                    boundary_respect=0.82,
                    emotional_variability=0.4,
                    behavior_vector=[0.68, 0.72, 0.48, 0.56, 0.69, 0.81],
                    behavior_uncertainty=[0.2] * 6,
                )
            )
        db.commit()

        created = recompute_matches_for_user(db, "usr-fallback-source", top_k=5)
        row = (
            db.query(MatchV2)
            .filter(
                MatchV2.user_id == "usr-fallback-source",
                MatchV2.other_user_id == "usr-fallback-candidate",
            )
            .first()
        )
        event_names = [row.event_name for row in db.query(AnalyticsEvent).filter(AnalyticsEvent.user_id == "usr-fallback-source").all()]
        assert created >= 1
        assert row is not None
        assert row.dynamics_payload["source_a"] == "psych_profile_fallback"
        assert row.dynamics_payload["source_b"] == "psych_profile_fallback"
        assert "psychology_fallback_used" in event_names
