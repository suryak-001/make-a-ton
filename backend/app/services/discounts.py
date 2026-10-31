"""Owner: A (step A2)."""

from collections.abc import Iterable
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.enums import DiscountScope
from app.models import Discount, Subscription


def open_discounts(db: Session, as_of: date) -> list[Discount]:
    """Discounts that are switched on, inside their dates and not used up, oldest first."""
    return list(
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


def discount_applies(discount: Discount, subscription: Subscription) -> bool:
    """Minimum purchase and quantity met, and the discount is scoped to this subscription itself
    (SUBSCRIPTION) or to a product on one of its lines (PRODUCT)."""
    subtotal = sum((line.unit_price * line.quantity for line in subscription.lines), start=0)
    quantity = sum(line.quantity for line in subscription.lines)
    if discount.min_purchase is not None and subtotal < discount.min_purchase:
        return False
    if discount.min_quantity is not None and quantity < discount.min_quantity:
        return False
    if discount.scope == DiscountScope.PRODUCT:
        product_ids = {line.product_id for line in subscription.lines}
        return bool(product_ids.intersection(p.id for p in discount.products))
    return subscription.id in {s.id for s in discount.subscriptions}


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
    return [d for d in open_discounts(db, as_of) if discount_applies(d, sub)]


def applicable_discounts_for_many(
    db: Session, subscriptions: Iterable[Subscription], as_of: date
) -> dict[int, list[Discount]]:
    """The same rule as `find_applicable_discounts`, for many subscriptions (their lines already loaded)
    with one query for the discounts. Subscriptions with no applicable discount are left out."""
    open_ones = open_discounts(db, as_of)
    found: dict[int, list[Discount]] = {}
    for sub in subscriptions:
        applicable = [d for d in open_ones if discount_applies(d, sub)]
        if applicable:
            found[sub.id] = applicable
    return found
