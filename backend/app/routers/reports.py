"""Database-side financial aggregates for the dashboard and reports. Every number is a SQL aggregate
(`func.sum`, `func.count`, `group_by`), never a loop over all rows. The one exception is the discount
adjustment to MRR, which looks only at the few subscriptions a discount touches."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import ColumnElement, Numeric, Select, case, cast, func, select
from sqlalchemy.orm import selectinload

from app.core.deps import Db, StaffUser
from app.enums import BillingPeriod, DiscountScope, InvoiceStatus, SubscriptionStatus
from app.models import Invoice, Payment, Plan, Subscription, SubscriptionLine
from app.schemas.money import InvoiceOut, RevenuePoint, SummaryOut
from app.services.billing import discount_reduction
from app.services.discounts import discount_applies, open_discounts
from app.services.invoice_queries import overdue_conditions, present_conditions
from app.services.money_views import INVOICE_LOAD, invoice_out

router = APIRouter(prefix="/api/reports", tags=["reports"])

ZERO = Decimal("0.00")
OVERDUE_LIST_LIMIT = 100
MONTHS_SHOWN = 12

# How many billing periods fit in a month (MRR is monthly-equivalent).
PERIODS_IN_A_MONTH = {
    BillingPeriod.DAILY: Decimal("30"),
    BillingPeriod.WEEKLY: Decimal("4.345"),
    BillingPeriod.MONTHLY: Decimal("1"),
    BillingPeriod.YEARLY: Decimal("0.083333"),
}
PERIODS_PER_MONTH = case(
    *((Plan.billing_period == period, factor) for period, factor in PERIODS_IN_A_MONTH.items()),
    else_=Decimal("1"),
)


def _money_sum(expression) -> ColumnElement:
    """SUM as a two-decimal amount, 0.00 when there are no rows (the API always sends money as "12.00")."""
    return cast(func.coalesce(func.sum(expression), 0), Numeric(12, 2))


@dataclass
class ReportFilters:
    from_date: date | None = None
    to_date: date | None = None
    plan_id: int | None = None
    customer_id: int | None = None
    status: InvoiceStatus | None = None  # of the invoices; by default Confirmed and Paid count


Filters = Annotated[ReportFilters, Depends()]


# ───────────────────────────── filters as SQL conditions ─────────────────────────────


def _invoice_conditions(f: ReportFilters) -> list:
    status = Invoice.status == f.status if f.status else Invoice.status.in_(_COUNTED_STATUSES)
    return [
        status,
        *present_conditions(
            (f.from_date, lambda v: Invoice.invoice_date >= v),
            (f.to_date, lambda v: Invoice.invoice_date <= v),
            (f.customer_id, lambda v: Invoice.customer_id == v),
            (f.plan_id, lambda v: Subscription.plan_id == v),
        ),
    ]


def _payment_conditions(f: ReportFilters) -> list:
    return present_conditions(
        (f.from_date, lambda v: Payment.payment_date >= v),
        (f.to_date, lambda v: Payment.payment_date <= v),
        (f.customer_id, lambda v: Invoice.customer_id == v),
        (f.plan_id, lambda v: Subscription.plan_id == v),
    )


def _who_conditions(f: ReportFilters) -> list:
    """Customer and plan only, for figures that are about right now (overdue)."""
    return present_conditions(
        (f.customer_id, lambda v: Invoice.customer_id == v),
        (f.plan_id, lambda v: Subscription.plan_id == v),
    )


_COUNTED_STATUSES = [InvoiceStatus.CONFIRMED, InvoiceStatus.PAID]


def _invoices_with_subscription(*columns) -> Select:
    return (
        select(*columns).select_from(Invoice).join(Subscription, Subscription.id == Invoice.subscription_id)
    )


def _payments_with_invoice(*columns) -> Select:
    return (
        select(*columns)
        .select_from(Payment)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .join(Subscription, Subscription.id == Invoice.subscription_id)
    )


# ───────────────────────────── the numbers ─────────────────────────────


def _active_subscriptions(db: Db, f: ReportFilters) -> int:
    conditions = present_conditions(
        (f.customer_id, lambda v: Subscription.customer_id == v),
        (f.plan_id, lambda v: Subscription.plan_id == v),
    )
    stmt = select(func.count()).where(Subscription.status == SubscriptionStatus.ACTIVE, *conditions)
    return db.scalar(stmt) or 0


def _monthly_recurring_revenue(db: Db, f: ReportFilters) -> Decimal:
    conditions = present_conditions(
        (f.customer_id, lambda v: Subscription.customer_id == v),
        (f.plan_id, lambda v: Subscription.plan_id == v),
    )
    monthly_amount = SubscriptionLine.unit_price * SubscriptionLine.quantity * PERIODS_PER_MONTH
    stmt = (
        select(_money_sum(monthly_amount))
        .select_from(SubscriptionLine)
        .join(Subscription, Subscription.id == SubscriptionLine.subscription_id)
        .join(Plan, Plan.id == Subscription.plan_id)
        .where(Subscription.status == SubscriptionStatus.ACTIVE, *conditions)
    )
    gross = db.scalar(stmt)
    return max(gross - _discounts_worth_per_month(db, conditions), ZERO)


def _discounts_worth_per_month(db: Db, conditions: list) -> Decimal:
    """What the discounts that apply today take off the active subscriptions, as a monthly amount, by the
    same rules billing uses. Only subscriptions a discount can touch are loaded."""
    today = date.today()
    discounts = open_discounts(db, today)
    ids = {s.id for d in discounts if d.scope == DiscountScope.SUBSCRIPTION for s in d.subscriptions}
    product_ids = {p.id for d in discounts if d.scope == DiscountScope.PRODUCT for p in d.products}
    if product_ids:
        ids |= set(db.scalars(select(SubscriptionLine.subscription_id).where(SubscriptionLine.product_id.in_(product_ids))))
    if not ids:
        return ZERO
    subscriptions = list(
        db.scalars(
            select(Subscription)
            .where(Subscription.id.in_(ids), Subscription.status == SubscriptionStatus.ACTIVE, *conditions)
            .options(selectinload(Subscription.lines), selectinload(Subscription.plan))
        )
    )
    worth = ZERO
    for sub in subscriptions:
        applicable = [d for d in discounts if discount_applies(d, sub)]
        if applicable:
            worth += discount_reduction(sub.lines, applicable) * PERIODS_IN_A_MONTH[sub.plan.billing_period]
    return worth.quantize(ZERO)


def _invoiced_and_outstanding(db: Db, f: ReportFilters) -> tuple[Decimal, Decimal]:
    stmt = _invoices_with_subscription(
        _money_sum(Invoice.total), _money_sum(Invoice.total - Invoice.amount_paid)
    ).where(*_invoice_conditions(f))
    invoiced, outstanding = db.execute(stmt).one()
    return invoiced, outstanding


def _collected(db: Db, f: ReportFilters) -> Decimal:
    stmt = _payments_with_invoice(_money_sum(Payment.amount)).where(*_payment_conditions(f))
    return db.scalar(stmt)


def _overdue_totals(db: Db, f: ReportFilters) -> tuple[int, Decimal]:
    stmt = _invoices_with_subscription(func.count(), _money_sum(Invoice.total - Invoice.amount_paid)).where(
        *overdue_conditions(), *_who_conditions(f)
    )
    count, amount = db.execute(stmt).one()
    return count, amount


# ───────────────────────────── endpoints ─────────────────────────────


@router.get("/summary", response_model=SummaryOut)
def summary(db: Db, _: StaffUser, filters: Filters):
    invoiced, outstanding = _invoiced_and_outstanding(db, filters)
    overdue_count, overdue_amount = _overdue_totals(db, filters)
    return SummaryOut(
        active_subscriptions=_active_subscriptions(db, filters),
        mrr=_monthly_recurring_revenue(db, filters),
        invoiced=invoiced,
        collected=_collected(db, filters),
        outstanding=outstanding,
        overdue_count=overdue_count,
        overdue_amount=overdue_amount,
    )


@router.get("/overdue", response_model=list[InvoiceOut])
def overdue(db: Db, _: StaffUser, filters: Filters):
    stmt = (
        select(Invoice)
        .join(Subscription, Subscription.id == Invoice.subscription_id)
        .where(*overdue_conditions(), *_who_conditions(filters))
        .options(*INVOICE_LOAD)
        .order_by(Invoice.due_date)
        .limit(OVERDUE_LIST_LIMIT)
    )
    return [invoice_out(row) for row in db.scalars(stmt).unique()]


@router.get("/revenue-by-month", response_model=list[RevenuePoint])
def revenue_by_month(db: Db, _: StaffUser, filters: Filters):
    invoiced = _totals_by_month(
        db,
        _invoices_with_subscription,
        Invoice.invoice_date,
        Invoice.total,
        _invoice_conditions(filters),
    )
    collected = _totals_by_month(
        db,
        _payments_with_invoice,
        Payment.payment_date,
        Payment.amount,
        _payment_conditions(filters),
    )
    months = sorted(invoiced.keys() | collected.keys())[-MONTHS_SHOWN:]
    return [
        RevenuePoint(month=m, invoiced=invoiced.get(m, ZERO), collected=collected.get(m, ZERO))
        for m in months
    ]


def _totals_by_month(db: Db, source, date_column, amount_column, conditions: list) -> dict[str, Decimal]:
    month = func.to_char(date_column, "YYYY-MM")
    stmt = source(month, _money_sum(amount_column)).where(*conditions).group_by(month)
    return {m: total for m, total in db.execute(stmt)}
