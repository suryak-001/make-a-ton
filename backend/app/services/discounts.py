"""Owner: A (step A2)."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.enums import DiscountScope
from app.models import Discount, Subscription


def find_applicable_discounts(db: Session, subscription_id: int, as_of: date) -> list[Discount]:
    """Discounts that apply to a subscription on a given date: active, within start/end dates,
    used_count < usage_limit, min purchase / min quantity met, and scoped to the subscription itself
    (SUBSCRIPTION) or to products on its lines (PRODUCT)."""
    sub = db.scalar(
        select(Subscription)
        .where(Subscription.id == subscription_id)
        .options(selectinload(Subscription.lines))
    )
    if sub is None:
        return []
    subtotal = sum((line.unit_price * line.quantity for line in sub.lines), start=0)
    quantity = sum(line.quantity for line in sub.lines)
    product_ids = {line.product_id for line in sub.lines}
    rows = list(
        db.scalars(
            select(Discount)
            .where(
                Discount.active.is_(True),
                Discount.start_date <= as_of,
                (Discount.end_date.is_(None) | (Discount.end_date >= as_of)),
                (Discount.usage_limit.is_(None) | (Discount.used_count < Discount.usage_limit)),
            )
            .options(selectinload(Discount.products), selectinload(Discount.subscriptions))
            .order_by(Discount.id)
        )
    )
    result = []
    for discount in rows:
        if discount.min_purchase is not None and subtotal < discount.min_purchase:
            continue
        if discount.min_quantity is not None and quantity < discount.min_quantity:
            continue
        if discount.scope == DiscountScope.PRODUCT:
            if not product_ids.intersection(p.id for p in discount.products):
                continue
        elif subscription_id not in {s.id for s in discount.subscriptions}:
            continue
        result.append(discount)
    return result
