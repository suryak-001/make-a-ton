"""Database-side financial aggregates for the dashboard and reports."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import case, func, select

from app.core.deps import Db, StaffUser
from app.enums import BillingPeriod, InvoiceStatus, SubscriptionStatus
from app.models import Invoice, Payment, Plan, Subscription, SubscriptionLine
from app.schemas.money import InvoiceOut, RevenuePoint, SummaryOut
from app.services.money_views import INVOICE_LOAD, invoice_out

router = APIRouter(prefix="/api/reports", tags=["reports"])

ZERO = Decimal("0")


@router.get("/summary", response_model=SummaryOut)
def summary(db: Db, _: StaffUser, from_date: date | None = None, to_date: date | None = None):
    invoice_filter = [Invoice.status.in_([InvoiceStatus.CONFIRMED, InvoiceStatus.PAID])]
    payment_filter = []
    if from_date:
        invoice_filter.append(Invoice.invoice_date >= from_date)
        payment_filter.append(Payment.payment_date >= from_date)
    if to_date:
        invoice_filter.append(Invoice.invoice_date <= to_date)
        payment_filter.append(Payment.payment_date <= to_date)

    active = (
        db.scalar(
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.status == SubscriptionStatus.ACTIVE)
        )
        or 0
    )
    multiplier = case(
        (Plan.billing_period == BillingPeriod.DAILY, Decimal("30")),
        (Plan.billing_period == BillingPeriod.WEEKLY, Decimal("4.345")),
        (Plan.billing_period == BillingPeriod.YEARLY, Decimal("0.083333")),
        else_=Decimal("1"),
    )
    mrr = (
        db.scalar(
            select(
                func.coalesce(
                    func.sum(SubscriptionLine.unit_price * SubscriptionLine.quantity * multiplier), 0
                )
            )
            .join(Subscription, Subscription.id == SubscriptionLine.subscription_id)
            .join(Plan, Plan.id == Subscription.plan_id)
            .where(Subscription.status == SubscriptionStatus.ACTIVE)
        )
        or ZERO
    )
    inv = db.execute(
        select(
            func.coalesce(func.sum(Invoice.total), 0),
            func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0),
        ).where(*invoice_filter)
    ).one()
    collected = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(*payment_filter)) or ZERO
    overdue_filter = [
        Invoice.status == InvoiceStatus.CONFIRMED,
        Invoice.due_date < date.today(),
        Invoice.amount_paid < Invoice.total,
    ]
    overdue = db.execute(
        select(func.count(), func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0)).where(
            *overdue_filter
        )
    ).one()
    return SummaryOut(
        active_subscriptions=active,
        mrr=mrr,
        invoiced=inv[0],
        collected=collected,
        outstanding=inv[1],
        overdue_count=overdue[0],
        overdue_amount=overdue[1],
    )


@router.get("/overdue", response_model=list[InvoiceOut])
def overdue(db: Db, _: StaffUser):
    rows = db.scalars(
        select(Invoice)
        .where(
            Invoice.status == InvoiceStatus.CONFIRMED,
            Invoice.due_date < date.today(),
            Invoice.amount_paid < Invoice.total,
        )
        .options(*INVOICE_LOAD)
        .order_by(Invoice.due_date)
        .limit(100)
    ).unique()
    return [invoice_out(row) for row in rows]


@router.get("/revenue-by-month", response_model=list[RevenuePoint])
def revenue_by_month(db: Db, _: StaffUser):
    invoice_month = func.to_char(func.date_trunc("month", Invoice.invoice_date), "YYYY-MM")
    payment_month = func.to_char(func.date_trunc("month", Payment.payment_date), "YYYY-MM")
    invoice_rows = {
        month: total
        for month, total in db.execute(
            select(invoice_month, func.sum(Invoice.total))
            .where(Invoice.status.in_([InvoiceStatus.CONFIRMED, InvoiceStatus.PAID]))
            .group_by(invoice_month)
        )
    }
    payment_rows = {
        month: total
        for month, total in db.execute(
            select(payment_month, func.sum(Payment.amount)).group_by(payment_month)
        )
    }
    months = sorted(set(invoice_rows) | set(payment_rows))[-12:]
    return [
        RevenuePoint(month=m, invoiced=invoice_rows.get(m, ZERO), collected=payment_rows.get(m, ZERO))
        for m in months
    ]
