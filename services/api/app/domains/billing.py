import asyncio
import logging
import uuid
from datetime import datetime

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuthUser, BillingProduct, PaymentEvent, Subscription
from ..security import get_current_auth_user, require_admin_user
from ..services.analytics import track as ph_track
from ..services.email import send_subscription_confirmed
from ..settings import get_settings

logger = logging.getLogger("soulmatch.billing")
router = APIRouter(prefix="/billing", tags=["billing"])

_SETTINGS = None


def _stripe():
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = get_settings()
    if not _SETTINGS.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="stripe_not_configured",
        )
    stripe.api_key = _SETTINGS.stripe_secret_key
    return stripe


# ── PLANS ─────────────────────────────────────────────────────────────────────

HARDCODED_PLANS = [
    {"code": "premium_monthly", "name": "SoulMatch Premium", "price_cents": 1499, "currency": "CAD"},
    {"code": "premium_yearly",  "name": "SoulMatch Premium (Annual)", "price_cents": 9900, "currency": "CAD"},
]


class PlanItem(BaseModel):
    code: str
    name: str
    price_cents: int
    currency: str


class PlanListResponse(BaseModel):
    ok: bool
    plans: list[PlanItem]


@router.get("/plans", response_model=PlanListResponse)
def list_plans(_current_user: AuthUser = Depends(get_current_auth_user)):
    return PlanListResponse(ok=True, plans=[PlanItem(**p) for p in HARDCODED_PLANS])


# ── STRIPE CHECKOUT SESSION ────────────────────────────────────────────────────

class CheckoutSessionRequest(BaseModel):
    product_code: str = Field(min_length=3, max_length=64)
    success_url: str = Field(default="soulmatch://billing/success")
    cancel_url: str = Field(default="soulmatch://billing/cancel")

    @field_validator("product_code")
    @classmethod
    def validate_product(cls, v: str) -> str:
        allowed = {p["code"] for p in HARDCODED_PLANS}
        if v not in allowed:
            raise ValueError("unknown_product_code")
        return v


class CheckoutSessionResponse(BaseModel):
    ok: bool
    session_id: str
    checkout_url: str
    payment_event_id: str


@router.post("/checkout-session", response_model=CheckoutSessionResponse, status_code=status.HTTP_201_CREATED)
def create_checkout_session(
    payload: CheckoutSessionRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    settings = get_settings()
    _stripe()  # validates key is set

    plan = next((p for p in HARDCODED_PLANS if p["code"] == payload.product_code), None)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product_not_found")

    payment_event_id = f"pay-{uuid.uuid4().hex[:16]}"

    # Determine recurring vs one-time
    is_subscription = "monthly" in payload.product_code or "yearly" in payload.product_code
    interval = "month" if "monthly" in payload.product_code else "year"

    try:
        session_params: dict = {
            "mode": "subscription" if is_subscription else "payment",
            "metadata": {
                "user_id": current_user.id,
                "product_code": payload.product_code,
                "payment_event_id": payment_event_id,
            },
            "success_url": payload.success_url,
            "cancel_url": payload.cancel_url,
            "client_reference_id": current_user.id,
        }

        if settings.stripe_premium_price_id and is_subscription:
            # Use a pre-created Stripe Price ID (set in Render dashboard)
            session_params["line_items"] = [
                {"price": settings.stripe_premium_price_id, "quantity": 1}
            ]
        else:
            # Inline price definition (works without pre-creating in Stripe dashboard)
            session_params["line_items"] = [
                {
                    "price_data": {
                        "currency": plan["currency"].lower(),
                        "unit_amount": plan["price_cents"],
                        "product_data": {"name": plan["name"]},
                        **({"recurring": {"interval": interval}} if is_subscription else {}),
                    },
                    "quantity": 1,
                }
            ]

        session = stripe.checkout.Session.create(**session_params)
    except stripe.StripeError as e:
        logger.error("stripe_checkout_session_failed", extra={"error": str(e), "user_id": current_user.id})
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="stripe_error")

    payment_event = PaymentEvent(
        id=payment_event_id,
        user_id=current_user.id,
        product_code=payload.product_code,
        amount_cents=plan["price_cents"],
        currency=plan["currency"],
        status="pending",
        provider_event_id=session.id,
        created_at=datetime.utcnow(),
    )
    db.add(payment_event)
    db.commit()

    logger.info("checkout_session_created", extra={"user_id": current_user.id, "product_code": payload.product_code})
    return CheckoutSessionResponse(
        ok=True,
        session_id=session.id,
        checkout_url=session.url,
        payment_event_id=payment_event_id,
    )


# ── SUBSCRIPTION STATUS ───────────────────────────────────────────────────────

class SubscriptionStatusResponse(BaseModel):
    class SubscriptionItem(BaseModel):
        id: str
        product_code: str
        status: str
        started_at: str
        ends_at: str | None = None

    ok: bool
    user_id: str
    active_subscription: SubscriptionItem | None = None


@router.get("/subscription", response_model=SubscriptionStatusResponse)
def get_subscription_status(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    sub = db.scalar(
        select(Subscription)
        .where(Subscription.user_id == current_user.id, Subscription.status == "active")
        .order_by(Subscription.started_at.desc())
        .limit(1)
    )
    if not sub:
        return SubscriptionStatusResponse(ok=True, user_id=current_user.id, active_subscription=None)

    return SubscriptionStatusResponse(
        ok=True,
        user_id=current_user.id,
        active_subscription=SubscriptionStatusResponse.SubscriptionItem(
            id=sub.id,
            product_code=sub.product_code,
            status=sub.status,
            started_at=sub.started_at.isoformat(),
            ends_at=sub.ends_at.isoformat() if sub.ends_at else None,
        ),
    )


# ── STRIPE WEBHOOK (public — no auth, verified by Stripe signature) ───────────

@router.post("/webhook/stripe", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="webhook_not_configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        stripe.api_key = settings.stripe_secret_key
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except stripe.SignatureVerificationError:
        logger.warning("stripe_webhook_invalid_signature")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_signature")
    except Exception as e:
        logger.error("stripe_webhook_parse_error", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="parse_error")

    event_type = event["type"]
    logger.info("stripe_webhook_received", extra={"event_type": event_type, "event_id": event["id"]})

    if event_type == "checkout.session.completed":
        session_obj = event["data"]["object"]
        _handle_checkout_completed(session_obj, db)
        provisioned_user_id = session_obj.get("metadata", {}).get("user_id") or session_obj.get("client_reference_id")
        if provisioned_user_id:
            settings = get_settings()
            product_code = session_obj.get("metadata", {}).get("product_code", "premium_monthly")
            ph_track("subscription_started", distinct_id=provisioned_user_id, properties={"product_code": product_code}, api_key=settings.posthog_api_key)
            auth_user = db.get(AuthUser, provisioned_user_id)
            if auth_user and settings.resend_api_key:
                asyncio.create_task(send_subscription_confirmed(to=auth_user.email, resend_api_key=settings.resend_api_key))

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        _handle_subscription_updated(event["data"]["object"], db)

    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(event["data"]["object"], db)

    return {"ok": True, "event_type": event_type}


def _handle_checkout_completed(session: dict, db: Session) -> None:
    payment_event_id = session.get("metadata", {}).get("payment_event_id")
    user_id = session.get("metadata", {}).get("user_id") or session.get("client_reference_id")
    product_code = session.get("metadata", {}).get("product_code", "premium_monthly")

    if not user_id:
        logger.warning("stripe_checkout_completed_missing_user_id", extra={"session_id": session.get("id")})
        return

    # Update or create payment event
    event_row = db.get(PaymentEvent, payment_event_id) if payment_event_id else None
    if event_row:
        event_row.status = "succeeded"
        event_row.provider_event_id = session.get("id")
    else:
        event_row = PaymentEvent(
            id=payment_event_id or f"pay-{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            product_code=product_code,
            amount_cents=session.get("amount_total") or 1499,
            currency=(session.get("currency") or "cad").upper(),
            status="succeeded",
            provider_event_id=session.get("id"),
            created_at=datetime.utcnow(),
        )
        db.add(event_row)

    # Provision subscription if not already active
    active = db.scalar(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.product_code == product_code,
            Subscription.status == "active",
        )
    )
    if not active:
        db.add(Subscription(
            id=f"sub-{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            product_code=product_code,
            status="active",
            started_at=datetime.utcnow(),
            ends_at=None,
            created_at=datetime.utcnow(),
        ))

    db.commit()
    logger.info("subscription_provisioned", extra={"user_id": user_id, "product_code": product_code})


def _handle_subscription_updated(stripe_sub: dict, db: Session) -> None:
    stripe_sub_id = stripe_sub.get("id", "")
    stripe_status = stripe_sub.get("status", "")
    customer_id = stripe_sub.get("customer", "")

    # Map Stripe status to our status
    our_status = "active" if stripe_status in ("active", "trialing") else "canceled"

    sub = db.scalar(
        select(Subscription).where(Subscription.id.like(f"%{stripe_sub_id[-8:]}%"))
    )
    if sub:
        sub.status = our_status
        if our_status == "canceled":
            sub.ends_at = datetime.utcnow()
        db.commit()
        logger.info("subscription_status_updated", extra={"stripe_sub_id": stripe_sub_id, "status": our_status})


def _handle_payment_failed(invoice: dict, db: Session) -> None:
    customer_id = invoice.get("customer", "")
    logger.warning("stripe_payment_failed", extra={"customer_id": customer_id})


# ── CUSTOMER PORTAL (let users manage/cancel their subscription) ──────────────

class PortalSessionResponse(BaseModel):
    ok: bool
    portal_url: str


@router.post("/portal", response_model=PortalSessionResponse)
def create_portal_session(
    request: Request,
    current_user: AuthUser = Depends(get_current_auth_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    _stripe()

    # Look up Stripe customer ID from most recent succeeded payment event
    recent_event = db.scalar(
        select(PaymentEvent)
        .where(PaymentEvent.user_id == current_user.id, PaymentEvent.status == "succeeded")
        .order_by(PaymentEvent.created_at.desc())
        .limit(1)
    )
    if not recent_event or not recent_event.provider_event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no_active_subscription")

    try:
        # Retrieve customer ID from the Checkout Session
        session = stripe.checkout.Session.retrieve(recent_event.provider_event_id)
        customer_id = session.customer
        if not customer_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="stripe_customer_not_found")

        portal = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url="soulmatch://billing/portal-return",
        )
    except stripe.StripeError as e:
        logger.error("stripe_portal_error", extra={"error": str(e), "user_id": current_user.id})
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="stripe_error")

    return PortalSessionResponse(ok=True, portal_url=portal.url)


# ── LEGACY INTERNAL WEBHOOK (admin-only, kept for testing) ───────────────────

class InternalWebhookRequest(BaseModel):
    payment_event_id: str = Field(min_length=3, max_length=128)
    provider_event_id: str = Field(min_length=3, max_length=128)
    status: str = Field(min_length=3, max_length=32)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        allowed = {"succeeded", "failed", "pending", "canceled"}
        normalized = value.lower()
        if normalized not in allowed:
            raise ValueError("invalid_status")
        return normalized


@router.post("/webhook/internal", response_model=dict, include_in_schema=False)
def internal_webhook(
    payload: InternalWebhookRequest,
    db: Session = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    event = db.get(PaymentEvent, payload.payment_event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment_event_not_found")

    if event.provider_event_id and event.provider_event_id != payload.provider_event_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="provider_event_conflict")

    allowed_transitions = {
        "pending": {"pending", "succeeded", "failed", "canceled"},
        "succeeded": {"succeeded"},
        "failed": {"failed"},
        "canceled": {"canceled"},
    }
    if payload.status not in allowed_transitions.get(event.status.lower(), {event.status.lower()}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="invalid_status_transition")

    event.status = payload.status
    event.provider_event_id = payload.provider_event_id

    if payload.status == "succeeded":
        active = db.scalar(
            select(Subscription).where(
                Subscription.user_id == event.user_id,
                Subscription.product_code == event.product_code,
                Subscription.status == "active",
            )
        )
        if not active:
            db.add(Subscription(
                id=f"sub-{uuid.uuid4().hex[:16]}",
                user_id=event.user_id,
                product_code=event.product_code,
                status="active",
                started_at=datetime.utcnow(),
                ends_at=None,
                created_at=datetime.utcnow(),
            ))

    db.commit()
    return {"ok": True, "payment_event_id": event.id, "status": event.status}


# ── RECONCILIATION (admin) ────────────────────────────────────────────────────

class BillingReconciliationResponse(BaseModel):
    ok: bool
    generated_at: str
    summary: dict
    missing_subscription_payment_ids: list[str]
    orphan_subscription_ids: list[str]
    duplicate_provider_event_ids: list[str]


@router.get("/reconciliation", response_model=BillingReconciliationResponse)
def billing_reconciliation(
    db: Session = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    generated_at = datetime.utcnow()
    payments = db.scalars(select(PaymentEvent)).all()
    subscriptions = db.scalars(select(Subscription)).all()

    succeeded_keys: set[tuple[str, str]] = set()
    missing_subscription_payment_ids: list[str] = []
    provider_event_to_payment_ids: dict[str, list[str]] = {}

    for payment in payments:
        if payment.provider_event_id:
            provider_event_to_payment_ids.setdefault(payment.provider_event_id, []).append(payment.id)
        if payment.status == "succeeded":
            key = (payment.user_id, payment.product_code)
            succeeded_keys.add(key)
            has_active = any(
                sub.user_id == payment.user_id
                and sub.product_code == payment.product_code
                and sub.status == "active"
                for sub in subscriptions
            )
            if not has_active:
                missing_subscription_payment_ids.append(payment.id)

    orphan_subscription_ids = [
        sub.id for sub in subscriptions
        if sub.status == "active" and (sub.user_id, sub.product_code) not in succeeded_keys
    ]
    duplicate_provider_event_ids = sorted(
        eid for eid, ids in provider_event_to_payment_ids.items() if len(ids) > 1
    )

    return {
        "ok": True,
        "generated_at": generated_at.isoformat(),
        "summary": {
            "payments_total": len(payments),
            "subscriptions_total": len(subscriptions),
            "missing_subscriptions": len(missing_subscription_payment_ids),
            "orphan_subscriptions": len(orphan_subscription_ids),
            "duplicate_provider_events": len(duplicate_provider_event_ids),
        },
        "missing_subscription_payment_ids": missing_subscription_payment_ids,
        "orphan_subscription_ids": orphan_subscription_ids,
        "duplicate_provider_event_ids": duplicate_provider_event_ids,
    }
