"""Owner: B — a customer's own subscriptions, with self-service pause / resume / close / renew.

Every query is scoped to the signed-in customer. Someone else's record is a 404, never a 403,
so its existence isn't leaked. Drafts are internal and are never shown.
"""

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.core.deps import CustomerUser, Db
from app.core.errors import NotFound
from app.core.pagination import Page, Pages, paginate
from app.enums import SubscriptionStatus
from app.models import Subscription, SubscriptionLine
from app.schemas.subscriptions import (
    PortalSubscriptionDetail,
    RenewIn,
    SubscriptionListItem,
    TransitionIn,
)
from app.services import subscriptions as svc
from app.services.subscription_views import load_detail, portal_detail

router = APIRouter(prefix="/api/portal-subscriptions", tags=["portal"])


def _customer_id(user) -> int:
    if user.customer is None:
        raise NotFound("Subscription not found")
    return user.customer.id


@router.get("", response_model=Page[SubscriptionListItem])
def list_mine(db: Db, user: CustomerUser, pages: Pages):
    if user.customer is None:
        return Page(items=[], total=0, page=pages.page, page_size=pages.page_size)
    total_expr = (
        select(func.coalesce(func.sum(SubscriptionLine.amount), 0))
        .where(SubscriptionLine.subscription_id == Subscription.id)
        .scalar_subquery()
    )
    base = select(Subscription).where(
        Subscription.customer_id == user.customer.id, Subscription.status != SubscriptionStatus.DRAFT
    )
    stmt = (
        base.add_columns(total_expr.label("total"))
        .options(joinedload(Subscription.customer), joinedload(Subscription.plan))
        .order_by(Subscription.id.desc())
    )
    rows, total = paginate(db, stmt, pages, scalars=False, count_from=base)
    items = [
        SubscriptionListItem(
            id=s.id,
            number=s.number,
            status=s.status,
            customer={"id": s.customer.id, "name": s.customer.name},
            plan={"id": s.plan.id, "name": s.plan.name, "billing_period": s.plan.billing_period},
            start_date=s.start_date,
            expiry_date=s.expiry_date,
            total=line_total,
        )
        for s, line_total in rows
    ]
    return Page(items=items, total=total, page=pages.page, page_size=pages.page_size)


@router.get("/{subscription_id}", response_model=PortalSubscriptionDetail)
def get_mine(subscription_id: int, db: Db, user: CustomerUser):
    sub = load_detail(db, subscription_id)
    if sub.customer_id != _customer_id(user) or sub.status == SubscriptionStatus.DRAFT:
        raise NotFound("Subscription not found")
    return portal_detail(sub)


@router.post("/{subscription_id}/transition", response_model=PortalSubscriptionDetail)
def transition_mine(subscription_id: int, body: TransitionIn, db: Db, user: CustomerUser):
    svc.customer_transition(db, user, subscription_id, body.to, body.reason)
    db.commit()
    return portal_detail(load_detail(db, subscription_id))


@router.post("/{subscription_id}/renew", response_model=PortalSubscriptionDetail)
def renew_mine(subscription_id: int, body: RenewIn, db: Db, user: CustomerUser):
    svc.customer_renew(db, user, subscription_id, body.reason)
    db.commit()
    return portal_detail(load_detail(db, subscription_id))
