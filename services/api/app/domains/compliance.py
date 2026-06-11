import hashlib
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Appeal,
    AuditLog,
    AuthUser,
    ConsentEvent,
    DeletionQueueItem,
    DeletionJob,
    ModerationAction,
    ModerationReport,
    PolicyDocument,
    PolicyVersion,
    User,
    UserBlock,
    UserPolicyAcceptance,
    UserRightsRequest,
    VendorProcessor,
    IncidentReport,
    LawEnforcementRequest,
    RetentionRule,
)
from ..rate_limit import limit_rights_requests
from ..security import get_current_auth_user, require_admin_user
from ..settings import get_settings
from ..modules.moderation.service import is_critical_reason
from ..modules.policy.service import sha256_text
from ..modules.safety_service import recipient_protection_flags, update_risk_for_event

router = APIRouter(tags=["compliance"])
settings = get_settings()

DEFAULT_POLICIES = [
    {
        "policy_id": "terms-of-service",
        "version": "v1",
        "locale": "en-CA",
        "jurisdiction": "GLOBAL",
        "platform": "all",
        "legal_basis": "contract",
        "title": "Terms of Service",
        "summary": "Rules for use, account eligibility, and service limitations.",
        "body": "You must be at least 18 years old. You are responsible for account activity and content.",
    },
    {
        "policy_id": "privacy-policy",
        "version": "v1",
        "locale": "en-CA",
        "jurisdiction": "GLOBAL",
        "platform": "all",
        "legal_basis": "legitimate_interest",
        "title": "Privacy Policy",
        "summary": "Data categories, legal basis, retention windows, and rights handling.",
        "body": "We process identity, birth, media, and messaging data for matching, safety, and operations.",
    },
    {
        "policy_id": "acceptable-use-policy",
        "version": "v1",
        "locale": "en-CA",
        "jurisdiction": "GLOBAL",
        "platform": "all",
        "legal_basis": "legal_obligation",
        "title": "Acceptable Use Policy",
        "summary": "Prohibited behavior, abuse prevention, and enforcement actions.",
        "body": "Harassment, exploitation, hate content, and illegal activities are prohibited.",
    },
    {
        "policy_id": "community-guidelines",
        "version": "v1",
        "locale": "en-CA",
        "jurisdiction": "GLOBAL",
        "platform": "all",
        "legal_basis": "legitimate_interest",
        "title": "Community Guidelines",
        "summary": "Behavioral expectations and reporting standards for user-generated content.",
        "body": "Use respectful communication and report harmful behavior through in-app tools.",
    },
    {
        "policy_id": "safety-and-moderation-policy",
        "version": "v1",
        "locale": "en-CA",
        "jurisdiction": "GLOBAL",
        "platform": "all",
        "legal_basis": "legal_obligation",
        "title": "Safety and Moderation Policy",
        "summary": "How moderation works, escalation process, and appeals pathway.",
        "body": "Reports are triaged by severity, reviewed by admins, and auditable decisions are recorded.",
    },
    {
        "policy_id": "data-retention-and-deletion",
        "version": "v1",
        "locale": "en-CA",
        "jurisdiction": "GLOBAL",
        "platform": "all",
        "legal_basis": "legal_obligation",
        "title": "Data Retention and Deletion",
        "summary": "Retention periods and propagation of deletion across subsystems.",
        "body": "Deletion requests propagate to DB, object storage, backups, search indexes, and analytics.",
    },
    {
        "policy_id": "law-enforcement-requests",
        "version": "v1",
        "locale": "en-CA",
        "jurisdiction": "GLOBAL",
        "platform": "all",
        "legal_basis": "legal_obligation",
        "title": "Law Enforcement Requests",
        "summary": "How legal demands are validated and processed.",
        "body": "Only valid, documented legal process is honored and logged in administrative audit trails.",
    },
]

LEGAL_BASIS_MAP = {
    "CA": ["consent", "contract", "legal_obligation", "legitimate_interest"],
    "US": ["consent", "contract", "legal_obligation", "legitimate_interest"],
    "EU": ["consent", "contract", "legal_obligation", "legitimate_interest", "vital_interest"],
    "UK": ["consent", "contract", "legal_obligation", "legitimate_interest", "vital_interest"],
    "GLOBAL": ["consent", "contract", "legal_obligation", "legitimate_interest"],
}

LEGAL_FRAMEWORK_MAP = {
    "CA": ["PIPEDA"],
    "US-CA": ["CCPA", "CPRA"],
    "EU": ["GDPR"],
    "UK": ["UK-GDPR", "DPA-2018"],
    "GLOBAL": ["PIPEDA", "GDPR-compatible", "CCPA-compatible"],
}


class PolicySummary(BaseModel):
    policy_id: str
    version: str
    locale: str
    jurisdiction: str
    platform: str
    legal_basis: str
    title: str
    summary: str
    published_at: str
    is_material_update: bool


class PolicyListResponse(BaseModel):
    ok: bool
    policies: list[PolicySummary]


class PolicyDetailResponse(BaseModel):
    ok: bool
    policy_id: str
    version: str
    locale: str
    jurisdiction: str
    platform: str
    legal_basis: str
    title: str
    summary: str
    body: str
    published_at: str
    is_material_update: bool
    attorney_review_required: bool


class ConsentRequest(BaseModel):
    policy_id: str = Field(min_length=2, max_length=64)
    policy_version: str = Field(min_length=1, max_length=32)
    consent_type: str = Field(min_length=2, max_length=64)
    granted: bool = True
    locale: str | None = Field(default=None, max_length=16)
    country: str | None = Field(default=None, max_length=8)
    jurisdiction: str | None = Field(default=None, max_length=16)
    platform: str | None = Field(default=None, max_length=16)
    legal_basis: str | None = Field(default=None, max_length=64)
    app_version: str | None = Field(default=None, max_length=32)


class ConsentResponse(BaseModel):
    ok: bool
    consent_id: int


class ConsentHistoryItem(BaseModel):
    consent_id: int
    policy_id: str
    policy_version: str
    consent_type: str
    granted: bool
    country: str | None
    locale: str | None
    timestamp: str


class ConsentHistoryResponse(BaseModel):
    ok: bool
    history: list[ConsentHistoryItem]


class UserRightsRequestPayload(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
    data: dict = Field(default_factory=dict)


class UserRightsResponse(BaseModel):
    ok: bool
    request_id: str
    status: str


class UserRightsListItem(BaseModel):
    request_id: str
    request_type: str
    status: str
    created_at: str
    completed_at: str | None = None


class UserRightsListResponse(BaseModel):
    ok: bool
    requests: list[UserRightsListItem]


class AppStoreComplianceResponse(BaseModel):
    ok: bool
    support_email: str
    policy_base_url: str
    account_delete_url: str
    attorney_review_required: bool
    backups_deletion_semantics: str


class IncidentRequest(BaseModel):
    severity: str = Field(min_length=3, max_length=32)
    summary: str = Field(min_length=5, max_length=4000)


class LawRequestPayload(BaseModel):
    request_reference: str = Field(min_length=3, max_length=128)
    jurisdiction: str = Field(min_length=2, max_length=32)
    notes: str | None = None


class ReportRequest(BaseModel):
    target_user_id: str | None = None
    message_id: int | None = None
    reason: str = Field(min_length=2, max_length=64)
    details: str | None = Field(default=None, max_length=2000)


class ReportResponse(BaseModel):
    ok: bool
    report_id: int


class SafetyTipsResponse(BaseModel):
    ok: bool
    tips: list[str]
    flags: dict


class BlockRequest(BaseModel):
    blocked_user_id: str
    reason: str | None = Field(default=None, max_length=64)


class BlockResponse(BaseModel):
    ok: bool
    block_id: int


class AppealRequest(BaseModel):
    report_id: int | None = None
    moderation_action_id: int | None = None
    body: str = Field(min_length=5, max_length=4000)


class AppealResponse(BaseModel):
    ok: bool
    appeal_id: int


class AdminReportItem(BaseModel):
    report_id: int
    reporter_user_id: str
    target_user_id: str | None
    message_id: int | None
    reason: str
    details: str | None
    status: str
    created_at: str


class AdminReportsResponse(BaseModel):
    ok: bool
    reports: list[AdminReportItem]


class AdminModerationRequest(BaseModel):
    user_id: str
    reason: str = Field(min_length=2, max_length=2000)
    report_id: int | None = None


class AdminReportActionRequest(BaseModel):
    action: str = Field(min_length=3, max_length=64)
    reason: str = Field(min_length=2, max_length=2000)
    target_user_id: str | None = None


class AdminModerationResponse(BaseModel):
    ok: bool
    action_id: int


class AuditItem(BaseModel):
    id: int
    scope: str
    actor_role: str
    action: str
    target_type: str | None
    target_id: str | None
    payload: dict
    created_at: str


class AuditResponse(BaseModel):
    ok: bool
    items: list[AuditItem]


class RetentionRuleItem(BaseModel):
    data_class: str
    ttl_days: int
    purge_mode: str
    applies_to_backups: bool
    legal_hold_allowed: bool


class RetentionRulesResponse(BaseModel):
    ok: bool
    rules: list[RetentionRuleItem]


def _resolve_user_context(db: Session, auth_user_id: str) -> tuple[str, str]:
    profile = db.get(User, auth_user_id)
    locale = profile.locale if profile and profile.locale else "en-CA"
    jurisdiction = profile.jurisdiction if profile and profile.jurisdiction else "GLOBAL"
    return locale, jurisdiction


def _critical_reason_code(reason: str) -> bool:
    return is_critical_reason(reason)


def _resolve_escalation_severity(reason: str) -> str:
    return "critical" if _critical_reason_code(reason) else "standard"


def _moderation_actor_id(db: Session, fallback_user_id: str) -> str:
    admin = db.scalar(select(AuthUser).where(AuthUser.role == "admin").limit(1))
    return admin.id if admin else fallback_user_id


def seed_default_policies(db: Session) -> None:
    for row in DEFAULT_POLICIES:
        existing = db.scalar(
            select(PolicyDocument).where(
                PolicyDocument.policy_id == row["policy_id"],
                PolicyDocument.version == row["version"],
                PolicyDocument.locale == row["locale"],
                PolicyDocument.jurisdiction == row["jurisdiction"],
                PolicyDocument.platform == row["platform"],
            )
        )
        if existing:
            continue
        db.add(PolicyDocument(**row, is_active=True, is_material_update=False, attorney_review_required=True))
    db.commit()


def seed_default_policy_versions(db: Session) -> None:
    rows = db.scalars(select(PolicyDocument).where(PolicyDocument.is_active.is_(True))).all()
    for row in rows:
        exists = db.scalar(
            select(PolicyVersion).where(
                PolicyVersion.policy_key == row.policy_id,
                PolicyVersion.version == row.version,
                PolicyVersion.locale == row.locale,
                PolicyVersion.jurisdiction == row.jurisdiction,
                PolicyVersion.platform == row.platform,
            )
        )
        if exists:
            continue
        db.add(
            PolicyVersion(
                policy_key=row.policy_id,
                version=row.version,
                locale=row.locale,
                jurisdiction=row.jurisdiction,
                platform=row.platform,
                effective_at=row.published_at,
                body_sha256=sha256_text(row.body),
            )
        )
    db.commit()


def seed_default_compliance_registers(db: Session) -> None:
    existing_vendor_names = {row.name for row in db.scalars(select(VendorProcessor)).all()}
    defaults = [
        {
            "name": "AWS",
            "purpose": "Cloud hosting, storage, and infrastructure",
            "data_categories": ["account", "messages", "media_metadata"],
            "transfer_mechanism": "SCC",
            "dpa_url": "https://aws.amazon.com/compliance/gdpr-center/",
            "subprocessor_country": "US",
            "data_transfer_region": "GLOBAL",
            "scc_reference": "AWS-DPA-SCC",
            "active": True,
        },
        {
            "name": "Sentry",
            "purpose": "Error monitoring and incident triage",
            "data_categories": ["diagnostic_events"],
            "transfer_mechanism": "SCC",
            "dpa_url": "https://sentry.io/legal/dpa/",
            "subprocessor_country": "US",
            "data_transfer_region": "GLOBAL",
            "scc_reference": "SENTRY-DPA-SCC",
            "active": True,
        },
    ]
    for row in defaults:
        if row["name"] in existing_vendor_names:
            continue
        db.add(VendorProcessor(**row))
    db.commit()


def _append_audit(
    db: Session,
    actor_user_id: str | None,
    actor_role: str,
    scope: str,
    action: str,
    target_type: str | None,
    target_id: str | None,
    payload: dict | None = None,
    evidence_ref: str | None = None,
) -> None:
    payload = payload or {}
    serial = json.dumps(
        {
            "actor_user_id": actor_user_id,
            "actor_role": actor_role,
            "scope": scope,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "payload": payload,
            "created_at": datetime.utcnow().isoformat(),
        },
        sort_keys=True,
    )
    immutable_hash = hashlib.sha256(serial.encode("utf-8")).hexdigest()
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            scope=scope,
            action=action,
            target_type=target_type,
            target_id=target_id,
            payload=payload,
            immutable_hash=immutable_hash,
            evidence_ref=evidence_ref,
        )
    )


def _create_rights_request(
    db: Session,
    user_id: str,
    right_type: str,
    payload: dict,
    locale: str | None = None,
    jurisdiction: str | None = None,
) -> UserRightsRequest:
    now = datetime.utcnow()
    req = UserRightsRequest(
        id=f"urr-{uuid.uuid4().hex[:16]}",
        user_id=user_id,
        right_type=right_type,
        status="pending",
        locale=locale,
        jurisdiction=jurisdiction,
        request_payload=payload,
        resolution_payload={},
        created_at=now,
        updated_at=now,
        completed_at=None,
    )
    db.add(req)
    return req


@router.get("/policies", response_model=PolicyListResponse)
def list_policies(
    locale: str = Query(default="en-CA", min_length=2, max_length=16),
    jurisdiction: str = Query(default="GLOBAL", min_length=2, max_length=16),
    platform: str = Query(default="all", min_length=2, max_length=16),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(PolicyDocument)
        .where(
            PolicyDocument.is_active.is_(True),
            PolicyDocument.locale == locale,
            PolicyDocument.jurisdiction.in_([jurisdiction, "GLOBAL"]),
            PolicyDocument.platform.in_([platform, "all"]),
        )
        .order_by(PolicyDocument.policy_id.asc())
    ).all()
    return {
        "ok": True,
        "policies": [
            {
                "policy_id": row.policy_id,
                "version": row.version,
                "locale": row.locale,
                "jurisdiction": row.jurisdiction,
                "platform": row.platform,
                "legal_basis": row.legal_basis,
                "title": row.title,
                "summary": row.summary,
                "published_at": row.published_at.isoformat(),
                "is_material_update": row.is_material_update,
            }
            for row in rows
        ],
    }


@router.get("/policies/{policy_id}", response_model=PolicyDetailResponse)
def get_policy(
    policy_id: str,
    locale: str = Query(default="en-CA", min_length=2, max_length=16),
    jurisdiction: str = Query(default="GLOBAL", min_length=2, max_length=16),
    platform: str = Query(default="all", min_length=2, max_length=16),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(PolicyDocument)
        .where(
            PolicyDocument.policy_id == policy_id,
            PolicyDocument.locale == locale,
            PolicyDocument.jurisdiction.in_([jurisdiction, "GLOBAL"]),
            PolicyDocument.platform.in_([platform, "all"]),
        )
        .order_by(desc(PolicyDocument.published_at))
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="policy_not_found")
    return {
        "ok": True,
        "policy_id": row.policy_id,
        "version": row.version,
        "locale": row.locale,
        "jurisdiction": row.jurisdiction,
        "platform": row.platform,
        "legal_basis": row.legal_basis,
        "title": row.title,
        "summary": row.summary,
        "body": row.body,
        "published_at": row.published_at.isoformat(),
        "is_material_update": row.is_material_update,
        "attorney_review_required": row.attorney_review_required,
    }


@router.get("/policies/{policy_id}/version/{version}", response_model=PolicyDetailResponse)
def get_policy_version(
    policy_id: str,
    version: str,
    locale: str = Query(default="en-CA", min_length=2, max_length=16),
    jurisdiction: str = Query(default="GLOBAL", min_length=2, max_length=16),
    platform: str = Query(default="all", min_length=2, max_length=16),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(PolicyDocument).where(
            PolicyDocument.policy_id == policy_id,
            PolicyDocument.version == version,
            PolicyDocument.locale == locale,
            PolicyDocument.jurisdiction.in_([jurisdiction, "GLOBAL"]),
            PolicyDocument.platform.in_([platform, "all"]),
        )
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="policy_version_not_found")
    return {
        "ok": True,
        "policy_id": row.policy_id,
        "version": row.version,
        "locale": row.locale,
        "jurisdiction": row.jurisdiction,
        "platform": row.platform,
        "legal_basis": row.legal_basis,
        "title": row.title,
        "summary": row.summary,
        "body": row.body,
        "published_at": row.published_at.isoformat(),
        "is_material_update": row.is_material_update,
        "attorney_review_required": row.attorney_review_required,
    }


@router.get("/policies/{policy_id}/versions/{version}", response_model=PolicyDetailResponse)
def get_policy_versions_alias(
    policy_id: str,
    version: str,
    locale: str = Query(default="en-CA", min_length=2, max_length=16),
    jurisdiction: str = Query(default="GLOBAL", min_length=2, max_length=16),
    platform: str = Query(default="all", min_length=2, max_length=16),
    db: Session = Depends(get_db),
):
    return get_policy_version(policy_id, version, locale, jurisdiction, platform, db)


@router.post("/consent", response_model=ConsentResponse)
def create_consent(
    payload: ConsentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
    x_app_version: str | None = Header(default=None, alias="X-App-Version"),
):
    now = datetime.utcnow()
    consent_hash = hashlib.sha256(
        json.dumps(
            {
                "user_id": current_user.id,
                "policy_id": payload.policy_id,
                "policy_version": payload.policy_version,
                "consent_type": payload.consent_type,
                "granted": payload.granted,
                "locale": payload.locale,
                "country": payload.country,
                "at": now.isoformat(),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    row = ConsentEvent(
        user_id=current_user.id,
        policy_id=payload.policy_id,
        policy_version=payload.policy_version,
        consent_type=payload.consent_type,
        granted=payload.granted,
        locale=payload.locale,
        country=payload.country,
        jurisdiction=payload.jurisdiction,
        platform=payload.platform or "all",
        legal_basis=payload.legal_basis or "consent",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        consent_hash=consent_hash,
        app_version=payload.app_version or x_app_version,
        consent_timestamp=now,
    )
    db.add(row)
    db.flush()

    if payload.consent_type in {"tos", "privacy"} and payload.granted:
        acceptance = db.get(UserPolicyAcceptance, current_user.id)
        if acceptance:
            if payload.consent_type == "tos":
                acceptance.tos_version = payload.policy_version
            if payload.consent_type == "privacy":
                acceptance.privacy_version = payload.policy_version
            acceptance.updated_at = now
        else:
            db.add(
                UserPolicyAcceptance(
                    user_id=current_user.id,
                    tos_version=payload.policy_version if payload.consent_type == "tos" else "unknown",
                    privacy_version=payload.policy_version if payload.consent_type == "privacy" else "unknown",
                    locale=payload.locale or "en-CA",
                    jurisdiction=payload.jurisdiction or payload.country or "GLOBAL",
                    platform=payload.platform or "all",
                    accepted_ip=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    app_version=payload.app_version or x_app_version,
                    accepted_policy_hash=consent_hash,
                    accepted_at=now,
                    updated_at=now,
                )
            )
        if acceptance:
            acceptance.locale = payload.locale or acceptance.locale
            acceptance.jurisdiction = payload.jurisdiction or payload.country or acceptance.jurisdiction
            acceptance.platform = payload.platform or acceptance.platform
            acceptance.accepted_ip = request.client.host if request.client else acceptance.accepted_ip
            acceptance.user_agent = request.headers.get("user-agent") or acceptance.user_agent
            acceptance.app_version = payload.app_version or x_app_version or acceptance.app_version
            acceptance.accepted_policy_hash = consent_hash

    _append_audit(
        db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        scope="user",
        action="consent.recorded",
        target_type="policy",
        target_id=f"{payload.policy_id}:{payload.policy_version}",
        payload={"consent_type": payload.consent_type, "granted": payload.granted},
    )
    db.commit()
    return {"ok": True, "consent_id": row.id}


@router.post("/consents", response_model=ConsentResponse)
def create_consent_alias(
    payload: ConsentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
    x_app_version: str | None = Header(default=None, alias="X-App-Version"),
):
    return create_consent(payload, request, db, current_user, x_app_version)


@router.get("/consent/history", response_model=ConsentHistoryResponse)
def get_consent_history(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    rows = db.scalars(
        select(ConsentEvent)
        .where(ConsentEvent.user_id == current_user.id)
        .order_by(desc(ConsentEvent.consent_timestamp))
    ).all()
    return {
        "ok": True,
        "history": [
            {
                "consent_id": row.id,
                "policy_id": row.policy_id,
                "policy_version": row.policy_version,
                "consent_type": row.consent_type,
                "granted": row.granted,
                "country": row.country,
                "locale": row.locale,
                "timestamp": row.consent_timestamp.isoformat(),
            }
            for row in rows
        ],
    }


@router.get("/consents/history", response_model=ConsentHistoryResponse)
def get_consent_history_alias(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    return get_consent_history(db, current_user)


@router.post("/user/export", response_model=UserRightsResponse)
def user_export(
    payload: UserRightsRequestPayload,
    _rl: None = Depends(limit_rights_requests),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    locale, jurisdiction = _resolve_user_context(db, current_user.id)
    req = _create_rights_request(
        db,
        current_user.id,
        "export",
        payload.model_dump(),
        locale=locale,
        jurisdiction=jurisdiction,
    )

    user_profile = db.get(User, current_user.id)
    message_count = db.query(ModerationReport).filter(ModerationReport.reporter_user_id == current_user.id).count()
    req.status = "completed"
    req.resolution_payload = {
        "profile_present": bool(user_profile),
        "report_count": message_count,
        "note": "Export preparation completed. Retrieve package from secure channel.",
    }
    req.updated_at = datetime.utcnow()
    req.completed_at = datetime.utcnow()

    _append_audit(
        db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        scope="user",
        action="rights.export.requested",
        target_type="user",
        target_id=current_user.id,
        payload={"request_id": req.id},
    )
    db.commit()
    return {"ok": True, "request_id": req.id, "status": req.status}


@router.post("/user/delete", response_model=UserRightsResponse)
def user_delete(
    payload: UserRightsRequestPayload,
    _rl: None = Depends(limit_rights_requests),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    locale, jurisdiction = _resolve_user_context(db, current_user.id)
    req = _create_rights_request(
        db,
        current_user.id,
        "delete",
        payload.model_dump(),
        locale=locale,
        jurisdiction=jurisdiction,
    )
    db.add(
        DeletionJob(
            id=f"djob-{uuid.uuid4().hex[:16]}",
            user_id=current_user.id,
            rights_request_id=req.id,
            status="queued",
            scope={"targets": ["database", "file_storage", "backups", "search_indexes", "analytics"]},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_error=None,
        )
    )
    for scope in ["database", "file_storage", "backups", "search_indexes", "analytics"]:
        db.add(
            DeletionQueueItem(
                user_id=current_user.id,
                right_request_id=req.id,
                scope=scope,
                status="queued",
            )
        )
    _append_audit(
        db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        scope="user",
        action="rights.delete.requested",
        target_type="user",
        target_id=current_user.id,
        payload={"request_id": req.id, "scopes": ["database", "file_storage", "backups", "search_indexes", "analytics"]},
    )
    db.commit()
    return {"ok": True, "request_id": req.id, "status": req.status}


@router.post("/user/correct", response_model=UserRightsResponse)
def user_correct(
    payload: UserRightsRequestPayload,
    _rl: None = Depends(limit_rights_requests),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    locale, jurisdiction = _resolve_user_context(db, current_user.id)
    req = _create_rights_request(
        db,
        current_user.id,
        "correct",
        payload.model_dump(),
        locale=locale,
        jurisdiction=jurisdiction,
    )
    profile = db.get(User, current_user.id)
    update_data = payload.data or {}
    if profile:
        if "name" in update_data:
            profile.name = str(update_data["name"]).strip()
        if "email" in update_data:
            profile.email = str(update_data["email"]).strip()
        if "birth_place" in update_data:
            profile.birth_place = str(update_data["birth_place"]).strip()

    req.status = "completed"
    req.resolution_payload = {"updated_fields": [k for k in ["name", "email", "birth_place"] if k in update_data]}
    req.updated_at = datetime.utcnow()
    req.completed_at = datetime.utcnow()

    _append_audit(
        db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        scope="user",
        action="rights.correct.requested",
        target_type="user",
        target_id=current_user.id,
        payload={"request_id": req.id},
    )
    db.commit()
    return {"ok": True, "request_id": req.id, "status": req.status}


@router.post("/user/restrict", response_model=UserRightsResponse)
def user_restrict_processing(
    payload: UserRightsRequestPayload,
    _rl: None = Depends(limit_rights_requests),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    locale, jurisdiction = _resolve_user_context(db, current_user.id)
    req = _create_rights_request(
        db,
        current_user.id,
        "restrict_processing",
        payload.model_dump(),
        locale=locale,
        jurisdiction=jurisdiction,
    )
    _append_audit(
        db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        scope="user",
        action="rights.restrict_processing.requested",
        target_type="user",
        target_id=current_user.id,
        payload={"request_id": req.id},
    )
    db.commit()
    return {"ok": True, "request_id": req.id, "status": req.status}


@router.post("/user/withdraw-consent", response_model=UserRightsResponse)
def user_withdraw_consent(
    payload: UserRightsRequestPayload,
    _rl: None = Depends(limit_rights_requests),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    locale, jurisdiction = _resolve_user_context(db, current_user.id)
    req = _create_rights_request(
        db,
        current_user.id,
        "withdraw_consent",
        payload.model_dump(),
        locale=locale,
        jurisdiction=jurisdiction,
    )
    _append_audit(
        db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        scope="user",
        action="rights.withdraw_consent.requested",
        target_type="user",
        target_id=current_user.id,
        payload={"request_id": req.id},
    )
    db.commit()
    return {"ok": True, "request_id": req.id, "status": req.status}


@router.post("/report", response_model=ReportResponse)
def report_content(
    payload: ReportRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if not payload.target_user_id and not payload.message_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_required")

    row = ModerationReport(
        reporter_user_id=current_user.id,
        target_user_id=payload.target_user_id,
        message_id=payload.message_id,
        reason=payload.reason,
        details=payload.details,
        status="open",
        severity=_resolve_escalation_severity(payload.reason),
        escalation_status="none",
    )
    db.add(row)
    db.flush()
    if _critical_reason_code(payload.reason):
        actor_id = _moderation_actor_id(db, current_user.id)
        row.status = "in_review"
        row.escalation_status = "critical_queue"
        row.escalated_at = datetime.utcnow()
        row.escalation_runbook_ref = "docs/compliance/CRITICAL_SAFETY_PLAYBOOK.md"
        db.add(
            ModerationAction(
                report_id=row.id,
                actor_admin_user_id=actor_id,
                target_user_id=payload.target_user_id or current_user.id,
                action_type="escalate_critical_safety",
                reason="automatic_escalation_from_reason_code",
                metadata_json={"reason": payload.reason.lower(), "severity": "critical"},
            )
        )
    _append_audit(
        db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        scope="user",
        action="moderation.report.created",
        target_type="report",
        target_id=str(row.id),
        payload={"reason": payload.reason},
    )
    if payload.target_user_id:
        update_risk_for_event(
            db,
            payload.target_user_id,
            "report_filed",
            {"report_filed": True, "reason": payload.reason.lower()},
        )
    db.commit()
    return {"ok": True, "report_id": row.id}


@router.post("/reports", response_model=ReportResponse)
def report_content_alias(
    payload: ReportRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    return report_content(payload, db, current_user)


@router.get("/safety/tips", response_model=SafetyTipsResponse)
def safety_tips(
    target_user_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    flags = recipient_protection_flags(db, target_user_id)
    tips = [
        "Avoid sharing phone numbers or addresses too early.",
        "Take your time before sending money or personal documents.",
        "Use block and report immediately if a conversation feels unsafe.",
    ]
    if flags.get("show_suspicious_pattern_warning"):
        tips.insert(0, "This person may be moving very fast. Consider slowing down before sharing personal info.")
    _append_audit(
        db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        scope="user",
        action="safety.tips.viewed",
        target_type="user",
        target_id=target_user_id or current_user.id,
        payload={"target_user_id": target_user_id},
    )
    db.commit()
    return {"ok": True, "tips": tips, "flags": flags}


@router.get("/rights/requests", response_model=UserRightsListResponse)
def list_rights_requests(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    rows = db.scalars(
        select(UserRightsRequest)
        .where(UserRightsRequest.user_id == current_user.id)
        .order_by(desc(UserRightsRequest.created_at))
        .limit(200)
    ).all()
    return {
        "ok": True,
        "requests": [
            {
                "request_id": row.id,
                "request_type": row.right_type,
                "status": row.status,
                "created_at": row.created_at.isoformat(),
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            }
            for row in rows
        ],
    }


@router.get("/rights/requests/{request_id}", response_model=UserRightsResponse)
def get_rights_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    row = db.get(UserRightsRequest, request_id)
    if not row or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rights_request_not_found")
    return {"ok": True, "request_id": row.id, "status": row.status}


@router.post("/rights/export", response_model=UserRightsResponse)
def rights_export(
    payload: UserRightsRequestPayload,
    _rl: None = Depends(limit_rights_requests),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    return user_export(payload=payload, db=db, current_user=current_user)


@router.post("/rights/delete", response_model=UserRightsResponse)
def rights_delete(
    payload: UserRightsRequestPayload,
    _rl: None = Depends(limit_rights_requests),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    return user_delete(payload=payload, db=db, current_user=current_user)


@router.get("/compliance/app-store", response_model=AppStoreComplianceResponse)
def app_store_compliance_meta():
    return {
        "ok": True,
        "support_email": settings.app_support_email,
        "policy_base_url": settings.app_policy_base_url,
        "account_delete_url": settings.app_account_delete_url,
        "attorney_review_required": True,
        "backups_deletion_semantics": "Deletion propagates immediately to active systems; encrypted backups purge on scheduled retention windows with audit evidence.",
    }


@router.get("/compliance/legal-basis-map")
def legal_basis_map():
    return {"ok": True, "legal_basis_map": LEGAL_BASIS_MAP, "framework_map": LEGAL_FRAMEWORK_MAP}


@router.get("/admin/retention/rules", response_model=RetentionRulesResponse)
def admin_retention_rules(
    db: Session = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    rows = db.scalars(select(RetentionRule).order_by(RetentionRule.data_class.asc())).all()
    return {
        "ok": True,
        "rules": [
            {
                "data_class": row.data_class,
                "ttl_days": row.ttl_days,
                "purge_mode": row.purge_mode,
                "applies_to_backups": row.applies_to_backups,
                "legal_hold_allowed": row.legal_hold_allowed,
            }
            for row in rows
        ],
    }


@router.get("/admin/safety/playbook")
def admin_safety_playbook(
    _admin_user: AuthUser = Depends(require_admin_user),
):
    return {
        "ok": True,
        "critical_reasons": ["minor", "csam", "sexual_content_minor", "violent_threat"],
        "workflow": [
            "quarantine content immediately",
            "open incident ticket",
            "assign moderator and legal owner",
            "preserve evidence and audit logs",
            "escalate lawful disclosures only via legal request workflow",
        ],
        "runbook_ref": "docs/compliance/CRITICAL_SAFETY_PLAYBOOK.md",
    }


@router.get("/admin/vendors")
def admin_vendors(
    db: Session = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    rows = db.scalars(select(VendorProcessor).order_by(VendorProcessor.name.asc())).all()
    return {
        "ok": True,
        "vendors": [
            {
                "id": row.id,
                "name": row.name,
                "purpose": row.purpose,
                "data_categories": row.data_categories,
                "transfer_mechanism": row.transfer_mechanism,
                "dpa_url": row.dpa_url,
                "subprocessor_country": row.subprocessor_country,
                "data_transfer_region": row.data_transfer_region,
                "scc_reference": row.scc_reference,
                "active": row.active,
            }
            for row in rows
        ],
    }


@router.post("/admin/incidents")
def admin_create_incident(
    payload: IncidentRequest,
    db: Session = Depends(get_db),
    admin_user: AuthUser = Depends(require_admin_user),
):
    row = IncidentReport(severity=payload.severity.lower(), summary=payload.summary, status="open")
    db.add(row)
    _append_audit(
        db,
        actor_user_id=admin_user.id,
        actor_role=admin_user.role,
        scope="admin",
        action="incident.created",
        target_type="incident",
        target_id=str(row.id),
        payload={"severity": payload.severity.lower()},
    )
    db.commit()
    return {"ok": True, "incident_id": row.id}


@router.post("/admin/law-enforcement")
def admin_law_enforcement(
    payload: LawRequestPayload,
    db: Session = Depends(get_db),
    admin_user: AuthUser = Depends(require_admin_user),
):
    existing = db.scalar(select(LawEnforcementRequest).where(LawEnforcementRequest.request_reference == payload.request_reference))
    if existing:
        return {"ok": True, "request_id": existing.id}
    row = LawEnforcementRequest(
        request_reference=payload.request_reference,
        jurisdiction=payload.jurisdiction,
        status="open",
        notes=payload.notes,
    )
    db.add(row)
    _append_audit(
        db,
        actor_user_id=admin_user.id,
        actor_role=admin_user.role,
        scope="admin",
        action="law_enforcement_request.created",
        target_type="law_enforcement_request",
        target_id=str(payload.request_reference),
        payload={"jurisdiction": payload.jurisdiction},
    )
    db.commit()
    return {"ok": True, "request_id": row.id}


@router.post("/block", response_model=BlockResponse)
def block_user(
    payload: BlockRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    if payload.blocked_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot_block_self")

    existing = db.scalar(
        select(UserBlock).where(
            UserBlock.blocker_user_id == current_user.id,
            UserBlock.blocked_user_id == payload.blocked_user_id,
        )
    )
    if existing:
        return {"ok": True, "block_id": existing.id}

    row = UserBlock(blocker_user_id=current_user.id, blocked_user_id=payload.blocked_user_id, reason=payload.reason)
    db.add(row)
    db.flush()
    _append_audit(
        db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        scope="user",
        action="moderation.user.blocked",
        target_type="user",
        target_id=payload.blocked_user_id,
        payload={"block_id": row.id, "reason": payload.reason},
    )
    db.commit()
    return {"ok": True, "block_id": row.id}


@router.post("/blocks", response_model=BlockResponse)
def block_user_alias(
    payload: BlockRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    return block_user(payload, db, current_user)


@router.delete("/blocks/{blocked_user_id}")
def unblock_user(
    blocked_user_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    row = db.scalar(
        select(UserBlock).where(
            UserBlock.blocker_user_id == current_user.id,
            UserBlock.blocked_user_id == blocked_user_id,
        )
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="block_not_found")
    db.delete(row)
    _append_audit(
        db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        scope="user",
        action="moderation.user.unblocked",
        target_type="user",
        target_id=blocked_user_id,
        payload={},
    )
    db.commit()
    return {"ok": True}


@router.post("/appeal", response_model=AppealResponse)
def create_appeal(
    payload: AppealRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    row = Appeal(
        user_id=current_user.id,
        report_id=payload.report_id,
        moderation_action_id=payload.moderation_action_id,
        body=payload.body,
        status="submitted",
    )
    db.add(row)
    db.flush()
    _append_audit(
        db,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        scope="user",
        action="moderation.appeal.created",
        target_type="appeal",
        target_id=str(row.id),
        payload={"report_id": payload.report_id, "moderation_action_id": payload.moderation_action_id},
    )
    db.commit()
    return {"ok": True, "appeal_id": row.id}


@router.get("/admin/reports", response_model=AdminReportsResponse)
def admin_list_reports(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    stmt = select(ModerationReport).order_by(desc(ModerationReport.created_at))
    if status_filter:
        stmt = stmt.where(ModerationReport.status == status_filter)
    rows = db.scalars(stmt.limit(200)).all()
    return {
        "ok": True,
        "reports": [
            {
                "report_id": row.id,
                "reporter_user_id": row.reporter_user_id,
                "target_user_id": row.target_user_id,
                "message_id": row.message_id,
                "reason": row.reason,
                "details": row.details,
                "status": row.status,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }


@router.post("/admin/reports/{report_id}/actions", response_model=AdminModerationResponse)
def admin_report_action(
    report_id: int,
    payload: AdminReportActionRequest,
    db: Session = Depends(get_db),
    admin_user: AuthUser = Depends(require_admin_user),
):
    report = db.get(ModerationReport, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report_not_found")

    target_user_id = payload.target_user_id or report.target_user_id or report.reporter_user_id
    action = ModerationAction(
        report_id=report.id,
        actor_admin_user_id=admin_user.id,
        target_user_id=target_user_id,
        action_type=payload.action,
        reason=payload.reason,
        metadata_json={"source": "admin_report_action"},
    )
    if payload.action in {"close_report", "resolved"}:
        report.status = "closed"
    elif payload.action in {"in_review", "escalate"}:
        report.status = "in_review"
    db.add(action)
    db.flush()
    _append_audit(
        db,
        actor_user_id=admin_user.id,
        actor_role=admin_user.role,
        scope="admin",
        action="moderation.report.action",
        target_type="report",
        target_id=str(report.id),
        payload={"moderation_action_id": action.id, "action": payload.action},
    )
    db.commit()
    return {"ok": True, "action_id": action.id}


def _admin_moderate_user(
    action_type: str,
    payload: AdminModerationRequest,
    db: Session,
    admin_user: AuthUser,
) -> dict:
    if payload.user_id == admin_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot_moderate_self")

    target_user = db.get(AuthUser, payload.user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    if target_user.role == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="cannot_moderate_admin")

    target_user.role = action_type
    action = ModerationAction(
        report_id=payload.report_id,
        actor_admin_user_id=admin_user.id,
        target_user_id=payload.user_id,
        action_type=action_type,
        reason=payload.reason,
        metadata_json={"source": "admin_api"},
    )
    db.add(action)
    db.flush()
    _append_audit(
        db,
        actor_user_id=admin_user.id,
        actor_role=admin_user.role,
        scope="admin",
        action=f"moderation.user.{action_type}",
        target_type="user",
        target_id=payload.user_id,
        payload={"action_id": action.id, "report_id": payload.report_id},
    )
    db.commit()
    return {"ok": True, "action_id": action.id}


@router.post("/admin/ban", response_model=AdminModerationResponse)
def admin_ban_user(
    payload: AdminModerationRequest,
    db: Session = Depends(get_db),
    admin_user: AuthUser = Depends(require_admin_user),
):
    return _admin_moderate_user("banned", payload, db, admin_user)


@router.post("/admin/users/{user_id}/ban", response_model=AdminModerationResponse)
def admin_ban_user_alias(
    user_id: str,
    payload: AdminModerationRequest,
    db: Session = Depends(get_db),
    admin_user: AuthUser = Depends(require_admin_user),
):
    payload.user_id = user_id
    return _admin_moderate_user("banned", payload, db, admin_user)


@router.post("/admin/suspend", response_model=AdminModerationResponse)
def admin_suspend_user(
    payload: AdminModerationRequest,
    db: Session = Depends(get_db),
    admin_user: AuthUser = Depends(require_admin_user),
):
    return _admin_moderate_user("suspended", payload, db, admin_user)


@router.post("/admin/users/{user_id}/suspend", response_model=AdminModerationResponse)
def admin_suspend_user_alias(
    user_id: str,
    payload: AdminModerationRequest,
    db: Session = Depends(get_db),
    admin_user: AuthUser = Depends(require_admin_user),
):
    payload.user_id = user_id
    return _admin_moderate_user("suspended", payload, db, admin_user)


@router.get("/audit/user", response_model=AuditResponse)
def user_audit_trail(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    rows = db.scalars(
        select(AuditLog)
        .where((AuditLog.actor_user_id == current_user.id) | (AuditLog.target_id == current_user.id))
        .order_by(desc(AuditLog.created_at))
        .limit(200)
    ).all()
    return {
        "ok": True,
        "items": [
            {
                "id": row.id,
                "scope": row.scope,
                "actor_role": row.actor_role,
                "action": row.action,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "payload": row.payload,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }


@router.get("/audit/admin", response_model=AuditResponse)
def admin_audit_trail(
    db: Session = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    rows = db.scalars(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(500)).all()
    return {
        "ok": True,
        "items": [
            {
                "id": row.id,
                "scope": row.scope,
                "actor_role": row.actor_role,
                "action": row.action,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "payload": row.payload,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }


@router.get("/admin/audit", response_model=AuditResponse)
def admin_audit_trail_alias(
    db: Session = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    return admin_audit_trail(db, _admin_user)
