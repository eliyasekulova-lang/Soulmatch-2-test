import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuthUser, BillingProduct, PaymentEvent, Subscription
from ..security import get_current_auth_user, require_admin_user

router = APIRouter(prefix="/billing", tags=["billing"])


class PlanItem(BaseModel):
    code: str
    name: str
    price_cents: int
    currency: str


class PlanListResponse(BaseModel):
    ok: bool
    plans: list[PlanItem]


class CheckoutIntentRequest(BaseModel):
    product_code: str = Field(min_length=3, max_length=64)
    currency: str = Field(min_length=3, max_length=3, default="USD")

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class CheckoutIntentResponse(BaseModel):
    ok: bool
    user_id: str
    payment_event_id: str
    product_code: str
    amount_cents: int
    currency: str
    checkout_status: str


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


class BillingWebhookRequest(BaseModel):
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


class BillingWebhookResponse(BaseModel):
    ok: bool
    payment_event_id: str
    status: str


class BillingReconciliationResponse(BaseModel):
    ok: bool
    generated_at: str
    summary: dict
    missing_subscription_payment_ids: list[str]
    orphan_subscription_ids: list[str]
    duplicate_provider_event_ids: list[str]


@router.get("/plans", response_model=PlanListResponse)
def list_plans(
    db: Session = Depends(get_db),
    _current_user: AuthUser = Depends(get_current_auth_user),
):
    rows = db.scalars(select(BillingProduct).where(BillingProduct.is_active.is_(True))).all()
    return PlanListResponse(
        ok=True,
        plans=[
            PlanItem(code=row.code, name=row.name, price_cents=row.price_cents, currency=row.currency)
            for row in rows
        ],
    )


@router.post("/checkout-intent", response_model=CheckoutIntentResponse)
def create_checkout_intent(
    payload: CheckoutIntentRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    product = db.get(BillingProduct, payload.product_code)
    if not product or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product_not_found")
    if payload.currency.upper() != product.currency.upper():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="currency_mismatch")

    payment_event = PaymentEvent(
        id=f"pay-{uuid.uuid4().hex[:16]}",
        user_id=current_user.id,
        product_code=product.code,
        amount_cents=product.price_cents,
        currency=product.currency,
        status="pending",
        provider_event_id=None,
        created_at=datetime.utcnow(),
    )
    db.add(payment_event)
    db.commit()

    return CheckoutIntentResponse(
        ok=True,
        user_id=current_user.id,
        payment_event_id=payment_event.id,
        product_code=product.code,
        amount_cents=product.price_cents,
        currency=product.currency,
        checkout_status="pending_provider_integration",
    )


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


@router.post("/webhook/provider", response_model=BillingWebhookResponse)
def provider_webhook(
    payload: BillingWebhookRequest,
    db: Session = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    event = db.get(PaymentEvent, payload.payment_event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment_event_not_found")

    # Replay-safe processing.
    if event.provider_event_id:
        if event.provider_event_id != payload.provider_event_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="provider_event_conflict")
        if event.status == payload.status:
            return {"ok": True, "payment_event_id": event.id, "status": event.status}

    existing_provider_event = db.scalar(
        select(PaymentEvent).where(
            PaymentEvent.provider_event_id == payload.provider_event_id,
            PaymentEvent.id != event.id,
        )
    )
    if existing_provider_event:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="provider_event_already_used")

    allowed_transitions = {
        "pending": {"pending", "succeeded", "failed", "canceled"},
        "succeeded": {"succeeded"},
        "failed": {"failed"},
        "canceled": {"canceled"},
    }
    current_status = event.status.lower()
    if payload.status not in allowed_transitions.get(current_status, {current_status}):
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
            db.add(
                Subscription(
                    id=f"sub-{uuid.uuid4().hex[:16]}",
                    user_id=event.user_id,
                    product_code=event.product_code,
                    status="active",
                    started_at=datetime.utcnow(),
                    ends_at=None,
                    created_at=datetime.utcnow(),
                )
            )

    db.commit()
    return {"ok": True, "payment_event_id": event.id, "status": event.status}


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
                sub.user_id == payment.user_id and sub.product_code == payment.product_code and sub.status == "active"
                for sub in subscriptions
            )
            if not has_active:
                missing_subscription_payment_ids.append(payment.id)

    orphan_subscription_ids: list[str] = []
    for sub in subscriptions:
        if sub.status != "active":
            continue
        key = (sub.user_id, sub.product_code)
        if key not in succeeded_keys:
            orphan_subscription_ids.append(sub.id)

    duplicate_provider_event_ids = sorted(
        [provider_event_id for provider_event_id, ids in provider_event_to_payment_ids.items() if len(ids) > 1]
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
