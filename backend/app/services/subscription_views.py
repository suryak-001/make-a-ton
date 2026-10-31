"""Owner: B — turns Subscription rows into API shapes (shared by staff, template and portal routers)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFound
from app.models import Subscription, SubscriptionLine
from app.schemas.subscriptions import (
    AddonOption,
    AddonsOut,
    AddonVariant,
    EventOut,
    LineOut,
    PlanDetail,
    PortalSubscriptionDetail,
    SubscriptionDetail,
    TaxOut,
)
from app.services.subscriptions import EDITABLE, addon_blocker, addon_products, allowed_actions

DETAIL_LOAD = (
    selectinload(Subscription.lines).selectinload(SubscriptionLine.product),
    selectinload(Subscription.lines).selectinload(SubscriptionLine.variant),
    selectinload(Subscription.lines).selectinload(SubscriptionLine.taxes),
    selectinload(Subscription.events),
)


def load_detail(db: Session, subscription_id: int) -> Subscription:
    sub = db.scalar(select(Subscription).where(Subscription.id == subscription_id).options(*DETAIL_LOAD))
    if sub is None:
        raise NotFound("Subscription not found")
    return sub


def _line(line: SubscriptionLine) -> LineOut:
    subtotal = line.unit_price * line.quantity
    return LineOut(
        id=line.id,
        product_id=line.product_id,
        product_name=line.product.name,
        variant_id=line.variant_id,
        variant_label=f"{line.variant.attribute}: {line.variant.value}" if line.variant else None,
        quantity=line.quantity,
        unit_price=line.unit_price,
        subtotal=subtotal,
        tax_amount=line.amount - subtotal,
        amount=line.amount,
        taxes=[TaxOut(id=t.id, name=t.name, kind=t.kind, rate=t.rate) for t in line.taxes],
        is_addon=line.product.is_addon,
    )


def _common(sub: Subscription, *, customer_view: bool, today: date) -> dict:
    lines = [_line(line) for line in sub.lines]
    zero = Decimal("0")
    return dict(
        id=sub.id,
        number=sub.number,
        status=sub.status,
        customer={"id": sub.customer.id, "name": sub.customer.name, "email": sub.customer.email},
        plan=PlanDetail(
            id=sub.plan.id,
            name=sub.plan.name,
            billing_period=sub.plan.billing_period,
            min_quantity=sub.plan.min_quantity,
            pausable=sub.plan.pausable,
            closable=sub.plan.closable,
            renewable=sub.plan.renewable,
            auto_close=sub.plan.auto_close,
        ),
        start_date=sub.start_date,
        expiry_date=sub.expiry_date,
        payment_term_days=sub.payment_term_days,
        quotation_valid_until=sub.quotation_valid_until,
        next_invoice_date=sub.next_invoice_date,
        created_at=sub.created_at,
        lines=lines,
        subtotal=sum((x.subtotal for x in lines), zero),
        tax_total=sum((x.tax_amount for x in lines), zero),
        total=sum((x.amount for x in lines), zero),
        events=[
            EventOut(
                id=e.id,
                from_status=e.from_status,
                to_status=e.to_status,
                reason=e.reason,
                actor_name=None if customer_view else (e.actor.name if e.actor else None),
                created_at=e.created_at,
            )
            for e in sub.events
        ],
        allowed_actions=allowed_actions(sub, sub.plan, today, customer=customer_view),
    )


def staff_detail(sub: Subscription, today: date | None = None) -> SubscriptionDetail:
    return SubscriptionDetail(
        **_common(sub, customer_view=False, today=today or date.today()),
        validity_days=sub.validity_days,
        notes=sub.notes,
        created_by=sub.created_by.name if sub.created_by else None,
        editable=sub.status in EDITABLE,
    )


def portal_detail(sub: Subscription, today: date | None = None) -> PortalSubscriptionDetail:
    return PortalSubscriptionDetail(**_common(sub, customer_view=True, today=today or date.today()))


def addons_out(db: Session, sub: Subscription, today: date | None = None) -> AddonsOut:
    """Every active add-on product, marked with the line it has on `sub` when it is switched on."""
    on = {line.product_id: line for line in sub.lines}
    blocker = addon_blocker(sub, today)
    return AddonsOut(
        editable=blocker is None,
        blocker=blocker,
        min_quantity=sub.plan.min_quantity,
        options=[
            AddonOption(
                product_id=p.id,
                name=p.name,
                notes=p.notes,
                unit_price=p.sales_price,
                taxes=[t.name for t in p.default_taxes if t.active],
                variants=[
                    AddonVariant(id=v.id, label=f"{v.attribute}: {v.value}", extra_price=v.extra_price)
                    for v in p.variants
                ],
                line_id=on[p.id].id if p.id in on else None,
                quantity=on[p.id].quantity if p.id in on else None,
            )
            for p in addon_products(db)
        ],
    )
