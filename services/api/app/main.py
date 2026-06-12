import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import SessionLocal, init_db
from .domains.auth import router as auth_router
from .domains.beta import router as beta_router
from .domains.astrology import router as astrology_router
from .domains.billing import router as billing_router
from .domains.compliance import router as compliance_router
from .domains.compliance import seed_default_compliance_registers, seed_default_policies, seed_default_policy_versions
from .domains.legal import router as legal_router
from .domains.legal import seed_legal_documents
from .domains.media import router as media_router
from .domains.matching import router as matching_router
from .domains.messaging import router as messaging_router
from .domains.onboarding import router as onboarding_router
from .domains.profile import router as profile_router
from .domains.psychology import router as psychology_router
from .domains.deep_assessment import router as deep_assessment_router
from .jobs.seed_psycho_items import seed_psycho_items
from .observability import configure_logging, init_sentry, install_audit_event_middleware, install_request_logging
from .runtime_state import mark_startup_error, mark_startup_ok
from .seed import seed_demo_candidates
from .settings import get_settings

settings = get_settings()
configure_logging(settings.log_level)
init_sentry(settings.sentry_dsn, settings.sentry_environment)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        init_db()
        if os.getenv("SEED_DEMO_CANDIDATES", "false").lower() == "true":
            with SessionLocal() as db:
                seed_demo_candidates(db)
        with SessionLocal() as db:
            seed_default_policies(db)
            seed_default_policy_versions(db)
            seed_default_compliance_registers(db)
            seed_legal_documents(db)
            seed_psycho_items(db)
        mark_startup_ok()
    except Exception as exc:
        mark_startup_error(str(exc))
        raise
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "auth", "description": "Authentication and token lifecycle"},
        {"name": "profile", "description": "User profile and onboarding"},
        {"name": "psychology", "description": "Psychology assessment sessions and self-report retrieval"},
        {"name": "astrology", "description": "Birth chart and vector generation"},
        {"name": "matching", "description": "Compatibility and recommendations"},
        {"name": "messaging", "description": "Messaging and threads"},
        {"name": "media", "description": "Media upload attachment and retrieval"},
        {"name": "billing", "description": "Billing and subscriptions"},
        {"name": "compliance", "description": "Policy, consent, rights, moderation, and audit"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
)
install_request_logging(app)
install_audit_event_middleware(app)


routers = [
    auth_router,
    beta_router,
    profile_router,
    onboarding_router,
    psychology_router,
    astrology_router,
    matching_router,
    messaging_router,
    media_router,
    billing_router,
    compliance_router,
    legal_router,
    deep_assessment_router,
]
for router in routers:
    app.include_router(router)
    app.include_router(router, prefix="/v1")
