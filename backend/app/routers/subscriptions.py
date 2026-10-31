"""Owner: B — subscriptions for admin and staff: list, edit, state changes, renewal, lifecycle job."""

from datetime import date

from fastapi import APIRouter, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import contains_eager, joinedload

from app.core.deps import AdminUser, Db, StaffUser
from app.core.pagination import Page, Pages, like_pattern, paginate
from app.enums import SubscriptionStatus
from app.models import Customer, Subscription, SubscriptionLine
from app.schemas.subscriptions import (
    LifecycleResult,
    RenewIn,
    SubscriptionDetail,
    SubscriptionIn,
    SubscriptionListItem,
    TransitionIn,
)
from app.services import subscriptions as svc
from app.services.subscription_views import load_detail, staff_detail

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("", response_model=Page[SubscriptionListItem])
def list_subscriptions(
    db: Db,
    _: StaffUser,
    pages: Pages,
    status: SubscriptionStatus | None = None,
    customer_id: int | None = None,
    plan_id: int | None = None,
    q: str | None = None,
):
    """Filters hit indexed columns (status, customer_id); `q` matches the number or customer name."""
    total_expr = (
        select(func.coalesce(func.sum(SubscriptionLine.amount), 0))
        .where(SubscriptionLine.subscription_id == Subscription.id)
        .scalar_subquery()
    )
    base = select(Subscription).join(Subscription.customer)
    if status:
        base = base.where(Subscription.status == status)
    if customer_id:
        base = base.where(Subscription.customer_id == customer_id)
    if plan_id:
        base = base.where(Subscription.plan_id == plan_id)
    if q and q.strip():
        like = like_pattern(q)
        base = base.where(
            or_(Subscription.number.ilike(like, escape="\\"), Customer.name.ilike(like, escape="\\"))
        )

    stmt = (
        base.add_columns(total_expr.label("total"))
        .options(contains_eager(Subscription.customer), joinedload(Subscription.plan))
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


@router.post("", response_model=SubscriptionDetail, status_code=status.HTTP_201_CREATED)
def create_subscription(body: SubscriptionIn, db: Db, user: StaffUser):
    sub = svc.create_subscription(db, body, user)
    db.commit()
    return staff_detail(load_detail(db, sub.id))


@router.post("/run-lifecycle", response_model=LifecycleResult)
def run_lifecycle(db: Db, _: AdminUser):
    """The daily job, runnable on demand: closes ended auto-close subscriptions, expires stale quotes."""
    result = svc.run_lifecycle_job(db, date.today())
    db.commit()
    return result


@router.get("/{subscription_id}", response_model=SubscriptionDetail)
def get_subscription(subscription_id: int, db: Db, _: StaffUser):
    return staff_detail(load_detail(db, subscription_id))


@router.put("/{subscription_id}", response_model=SubscriptionDetail)
def update_subscription(subscription_id: int, body: SubscriptionIn, db: Db, _: StaffUser):
    svc.update_subscription(db, subscription_id, body)
    db.commit()
    return staff_detail(load_detail(db, subscription_id))


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(subscription_id: int, db: Db, _: StaffUser):
    svc.delete_subscription(db, subscription_id)
    db.commit()


@router.post("/{subscription_id}/transition", response_model=SubscriptionDetail)
def transition(subscription_id: int, body: TransitionIn, db: Db, user: StaffUser):
    svc.transition_subscription(db, subscription_id, body.to, actor=user, reason=body.reason)
    db.commit()
    return staff_detail(load_detail(db, subscription_id))


@router.post("/{subscription_id}/renew", response_model=SubscriptionDetail)
def renew(subscription_id: int, body: RenewIn, db: Db, user: StaffUser):
    svc.renew_subscription(db, subscription_id, actor=user, reason=body.reason)
    db.commit()
    return staff_detail(load_detail(db, subscription_id))
