"""Owner: B — billing plans. Staff can read; only the admin can change them."""

from datetime import date

from fastapi import APIRouter, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import AdminUser, Db, StaffUser
from app.core.errors import Conflict
from app.core.lookup import get_or_404
from app.core.pagination import Page, Pages, like_pattern, paginate
from app.models import Plan, Subscription
from app.schemas.catalog import PlanIn, PlanOut
from app.services.subscriptions import LIVE

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.get("", response_model=Page[PlanOut])
def list_plans(
    db: Db,
    _: StaffUser,
    pages: Pages,
    q: str | None = None,
    active: bool | None = None,
    available: bool | None = None,
):
    """`available=true` = what can be picked for a new subscription today: active and inside its window."""
    stmt = select(Plan).order_by(Plan.name, Plan.id)
    if active is not None:
        stmt = stmt.where(Plan.active == active)
    if available:
        today = date.today()
        stmt = stmt.where(
            Plan.active.is_(True),
            or_(Plan.available_from.is_(None), Plan.available_from <= today),
            or_(Plan.available_to.is_(None), Plan.available_to >= today),
        )
    if q and q.strip():
        stmt = stmt.where(Plan.name.ilike(like_pattern(q), escape="\\"))
    rows, total = paginate(db, stmt, pages)
    return Page(items=rows, total=total, page=pages.page, page_size=pages.page_size)


@router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(body: PlanIn, db: Db, _: AdminUser):
    plan = Plan(**body.model_dump())
    db.add(plan)
    db.commit()
    return plan


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: int, db: Db, _: StaffUser):
    return get_or_404(db, Plan, plan_id)


@router.put("/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: int, body: PlanIn, db: Db, _: AdminUser):
    plan = get_or_404(db, Plan, plan_id)
    if body.billing_period != plan.billing_period and db.scalar(
        select(Subscription.id).where(Subscription.plan_id == plan.id, Subscription.status.in_(LIVE)).limit(1)
    ):
        # Billing dates follow the plan's period from each start date; changing it mid-way would break them.
        raise Conflict("Active or paused subscriptions use this plan, so its billing period can't change.")
    for field, value in body.model_dump().items():
        setattr(plan, field, value)
    db.commit()
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(plan_id: int, db: Db, _: AdminUser):
    plan = get_or_404(db, Plan, plan_id)
    db.delete(plan)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict("This plan is used by subscriptions or templates. Mark it inactive instead.") from None
