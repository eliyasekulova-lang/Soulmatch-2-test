from datetime import date, datetime, time

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, SmallInteger, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    birth_date: Mapped[str] = mapped_column(String(10), nullable=False)
    birth_time: Mapped[str] = mapped_column(String(5), nullable=False)
    birth_place: Mapped[str] = mapped_column(Text, nullable=False)
    birth_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    birth_country: Mapped[str | None] = mapped_column(String(255), nullable=True)
    birth_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    birth_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    birth_timezone: Mapped[str | None] = mapped_column(String(128), nullable=True)
    birth_date_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    birth_time_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    birth_place_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en-CA")
    jurisdiction: Mapped[str] = mapped_column(String(16), nullable=False, default="CA")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    goals: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    matching_preference: Mapped[str] = mapped_column(String(32), nullable=False, default="psych_behavior_astro")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AuthUser(Base):
    __tablename__ = "auth_users"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AstroVector(Base):
    __tablename__ = "astro_vectors"

    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    vector: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PsychProfile(Base):
    __tablename__ = "psych_profiles"

    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    ocean_vector: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    attachment_style: Mapped[str] = mapped_column(String(32), nullable=False, default="secure")
    attachment_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    love_language: Mapped[str] = mapped_column(String(64), nullable=False, default="quality_time")
    communication_style: Mapped[str] = mapped_column(String(64), nullable=False, default="direct")
    conflict_style: Mapped[str] = mapped_column(String(64), nullable=False, default="collaborative")
    social_energy: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    novelty_preference: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    boundaries_preference: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    source_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class OnboardingAnswer(Base):
    __tablename__ = "onboarding_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    section: Mapped[str] = mapped_column(String(64), nullable=False)
    question_id: Mapped[str] = mapped_column(String(64), nullable=False)
    answer: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    highlights: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    privacy_accepted: Mapped[bool] = mapped_column(nullable=False)
    sensitive_data_accepted: Mapped[bool] = mapped_column(nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    accepted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    event_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"
    __table_args__ = (UniqueConstraint("user_id", "experiment_key", name="ux_experiment_assignments_user_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    experiment_key: Mapped[str] = mapped_column(String(64), nullable=False)
    variant_key: Mapped[str] = mapped_column(String(64), nullable=False)
    assignment_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class BehaviorSignalEvent(Base):
    __tablename__ = "behavior_signal_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    event_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class BehaviorProfile(Base):
    __tablename__ = "behavior_profiles"

    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), primary_key=True)
    reply_time_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    conversation_depth_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    consistency_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    receptiveness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    boundary_respect_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    initiation_balance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    behavior_vector: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class TrustSafetyRisk(Base):
    __tablename__ = "trust_safety_risks"

    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), primary_key=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_band: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class SafetyActionLog(Base):
    __tablename__ = "safety_action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class MessageThread(Base):
    __tablename__ = "message_threads"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    pair_key: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    user_a_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_b_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thread_id: Mapped[str] = mapped_column(String(128), ForeignKey("message_threads.id", ondelete="CASCADE"), nullable=False)
    sender_user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipient_user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    hidden_by_safety: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    client_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class BillingProduct(Base):
    __tablename__ = "billing_products"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price_cents: Mapped[int] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    product_code: Mapped[str] = mapped_column(String(64), ForeignKey("billing_products.code", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    product_code: Mapped[str] = mapped_column(String(64), ForeignKey("billing_products.code", ondelete="RESTRICT"), nullable=False)
    amount_cents: Mapped[int] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PolicyDocument(Base):
    __tablename__ = "policy_documents"
    __table_args__ = (
        UniqueConstraint(
            "policy_id",
            "version",
            "locale",
            "jurisdiction",
            "platform",
            name="ux_policy_documents_identity_v2",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en-CA")
    jurisdiction: Mapped[str] = mapped_column(String(16), nullable=False, default="GLOBAL")
    platform: Mapped[str] = mapped_column(String(16), nullable=False, default="all")
    legal_basis: Mapped[str] = mapped_column(String(64), nullable=False, default="contract")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_material_update: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attorney_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    attorney_approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attorney_approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ConsentEvent(Base):
    __tablename__ = "consent_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    locale: Mapped[str | None] = mapped_column(String(16), nullable=True)
    country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(16), nullable=True)
    legal_basis: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    consent_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    consent_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class UserPolicyAcceptance(Base):
    __tablename__ = "user_policy_acceptance"

    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tos_version: Mapped[str] = mapped_column(String(32), nullable=False)
    privacy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en-CA")
    jurisdiction: Mapped[str] = mapped_column(String(16), nullable=False, default="GLOBAL")
    platform: Mapped[str] = mapped_column(String(16), nullable=False, default="all")
    accepted_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    accepted_policy_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    accepted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class UserRightsRequest(Base):
    __tablename__ = "user_rights_requests"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    right_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    locale: Mapped[str | None] = mapped_column(String(16), nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    resolution_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DeletionQueueItem(Base):
    __tablename__ = "deletion_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    right_request_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("user_rights_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    due_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ModerationReport(Base):
    __tablename__ = "moderation_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporter_user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_user_id: Mapped[str | None] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    message_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="standard")
    escalation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    escalation_runbook_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class UserBlock(Base):
    __tablename__ = "user_blocks"
    __table_args__ = (UniqueConstraint("blocker_user_id", "blocked_user_id", name="ux_user_blocks_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    blocker_user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    blocked_user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ModerationAction(Base):
    __tablename__ = "moderation_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("moderation_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_admin_user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Appeal(Base):
    __tablename__ = "appeals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    report_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("moderation_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    moderation_action_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("moderation_actions.id", ondelete="SET NULL"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    immutable_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RetentionRule(Base):
    __tablename__ = "retention_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_class: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    ttl_days: Mapped[int] = mapped_column(Integer, nullable=False)
    legal_hold_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    purge_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="hard_delete")
    applies_to_backups: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class VendorProcessor(Base):
    __tablename__ = "vendor_processors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    data_categories: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    transfer_mechanism: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dpa_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    subprocessor_country: Mapped[str | None] = mapped_column(String(32), nullable=True)
    data_transfer_region: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scc_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class IncidentReport(Base):
    __tablename__ = "incident_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LawEnforcementRequest(Base):
    __tablename__ = "law_enforcement_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_reference: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    jurisdiction: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint(
            "policy_key",
            "version",
            "locale",
            "jurisdiction",
            "platform",
            name="ux_policy_versions_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en-CA")
    jurisdiction: Mapped[str] = mapped_column(String(16), nullable=False, default="GLOBAL")
    platform: Mapped[str] = mapped_column(String(16), nullable=False, default="all")
    effective_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    body_sha256: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ConversationMember(Base):
    __tablename__ = "conversation_members"

    conversation_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MediaObject(Base):
    __tablename__ = "media_objects"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(String(128), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    message_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    media_type: Mapped[str] = mapped_column(String(16), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    attached_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporter_user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    reported_user_id: Mapped[str | None] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(128), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    message_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    media_id: Mapped[str | None] = mapped_column(String(128), ForeignKey("media_objects.id", ondelete="SET NULL"), nullable=True)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DeletionJob(Base):
    __tablename__ = "deletion_jobs"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    rights_request_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("user_rights_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    scope: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="system")
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class LegalConsent(Base):
    __tablename__ = "legal_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receipt_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LegalDocument(Base):
    __tablename__ = "legal_documents"
    __table_args__ = (UniqueConstraint("key", "version", name="ux_legal_documents_key_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class UserConsent(Base):
    __tablename__ = "user_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    doc_key: Mapped[str] = mapped_column(String(64), nullable=False)
    doc_version: Mapped[str] = mapped_column(String(32), nullable=False)
    consented_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)


class PrivacyRequest(Base):
    __tablename__ = "privacy_requests"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class JobRunTelemetry(Base):
    __tablename__ = "job_run_telemetry"

    job_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    last_run_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


PROFILE_STAGE = Enum("incomplete", "calibrating", "eligible", name="profile_stage")


class UserProfileState(Base):
    __tablename__ = "user_profile_state"

    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    stage: Mapped[str] = mapped_column(PROFILE_STAGE, nullable=False, default="incomplete")
    astro_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    psycho_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    required_modules_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_pass: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    astro_completion: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    psycho_completion: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    behavior_completion: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    astro_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    psycho_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    behavior_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class BirthData(Base):
    __tablename__ = "birth_data"

    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    birth_time: Mapped[time] = mapped_column(Time, nullable=False)
    birth_place_name: Mapped[str] = mapped_column(Text, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    timezone_iana: Mapped[str] = mapped_column(String(128), nullable=False)
    birth_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    dst_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class NatalChart(Base):
    __tablename__ = "natal_chart"

    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    asc_sign: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    asc_deg: Mapped[float] = mapped_column(Float, nullable=False)
    planets: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    aspects: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    astro_features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    astro_vector: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PsychoItem(Base):
    __tablename__ = "psycho_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    reverse_key: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trait_key: Mapped[str] = mapped_column(String(64), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False, default="likert")
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    dimension_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    followup_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class PsychoAssessmentSession(Base):
    __tablename__ = "psycho_assessment_sessions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    assessment_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    device_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PsychoItemResponse(Base):
    __tablename__ = "psycho_item_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("psycho_assessment_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id: Mapped[str] = mapped_column(String(64), ForeignKey("psycho_items.id", ondelete="CASCADE"), nullable=False)
    answer_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_answer_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_answer_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    considered_answer_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    changed_answer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    skipped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    returned_to_question: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uncertainty_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    free_text_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PsychoDerivedPattern(Base):
    __tablename__ = "psycho_derived_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    pattern_key: Mapped[str] = mapped_column(String(64), nullable=False)
    pattern_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    contributing_dimensions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    explanation_internal: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PsychoReport(Base):
    __tablename__ = "psycho_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("psycho_assessment_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    report_version: Mapped[str] = mapped_column(String(32), nullable=False)
    personality_summary: Mapped[str] = mapped_column(Text, nullable=False)
    relationship_style: Mapped[str] = mapped_column(Text, nullable=False)
    conflict_style: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_style: Mapped[str] = mapped_column(Text, nullable=False)
    affection_needs: Mapped[str] = mapped_column(Text, nullable=False)
    blind_spots: Mapped[str] = mapped_column(Text, nullable=False)
    best_match_type: Mapped[str] = mapped_column(Text, nullable=False)
    growth_suggestions: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PsychoResponse(Base):
    __tablename__ = "psycho_responses"

    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    item_id: Mapped[str] = mapped_column(String(64), ForeignKey("psycho_items.id", ondelete="CASCADE"), primary_key=True)
    answer: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    response_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PsychoScore(Base):
    __tablename__ = "psycho_scores"

    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    o: Mapped[float] = mapped_column(Float, nullable=False)
    c: Mapped[float] = mapped_column(Float, nullable=False)
    e: Mapped[float] = mapped_column(Float, nullable=False)
    a: Mapped[float] = mapped_column(Float, nullable=False)
    n: Mapped[float] = mapped_column(Float, nullable=False)
    att_anxiety: Mapped[float] = mapped_column(Float, nullable=False)
    att_avoid: Mapped[float] = mapped_column(Float, nullable=False)
    reassurance_need: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    independence_need: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    vulnerability_comfort: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    conflict_direct: Mapped[float] = mapped_column(Float, nullable=False)
    conflict_avoid: Mapped[float] = mapped_column(Float, nullable=False)
    conflict_delay: Mapped[float] = mapped_column(Float, nullable=False)
    emotional_regulation: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    value_stability: Mapped[float] = mapped_column(Float, nullable=False)
    value_novelty: Mapped[float] = mapped_column(Float, nullable=False)
    aff_attention: Mapped[float] = mapped_column(Float, nullable=False)
    aff_touch: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    aff_words: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    aff_acts: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    aff_gifts: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    psycho_vector: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    psycho_uncertainty: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    quality_flags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class BehaviorFeature(Base):
    __tablename__ = "behavior_features"

    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    response_consistency: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    response_delay_var: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    initiative_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    conversation_balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    engagement_stability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    boundary_respect: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    emotional_variability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    behavior_vector: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    behavior_uncertainty: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class MatchV2(Base):
    __tablename__ = "matches_v2"

    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    other_user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    psycho_score: Mapped[float] = mapped_column(Float, nullable=False)
    astro_score: Mapped[float] = mapped_column(Float, nullable=False)
    behavior_score: Mapped[float] = mapped_column(Float, nullable=False)
    compatibility_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    dynamics_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    explanation: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
