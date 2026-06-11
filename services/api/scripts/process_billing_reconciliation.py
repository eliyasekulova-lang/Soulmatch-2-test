from datetime import datetime

from sqlalchemy import select

from app.database import SessionLocal
from app.models import PaymentEvent, Subscription


def main() -> None:
    with SessionLocal() as db:
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
        if (sub.user_id, sub.product_code) not in succeeded_keys:
            orphan_subscription_ids.append(sub.id)

    duplicate_provider_event_ids = sorted(
        [provider_event_id for provider_event_id, ids in provider_event_to_payment_ids.items() if len(ids) > 1]
    )

    print(
        {
            "ok": True,
            "generated_at": datetime.utcnow().isoformat(),
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
    )


if __name__ == "__main__":
    main()
