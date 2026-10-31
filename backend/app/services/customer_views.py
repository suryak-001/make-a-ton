"""One customer on one page: the dashboard's numbers for them, what they subscribe to, what they were billed and
paid, and a single timeline of everything that happened to their account."""

from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import Numeric, cast, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Customer, Invoice, Payment, Subscription, SubscriptionEvent, SubscriptionLine
from app.schemas.money import InvoiceOut, PaymentOut, SummaryOut
from app.schemas.people import CustomerOut, TimelineItem
from app.schemas.subscriptions import SubscriptionListItem
from app.services.money_views import INVOICE_LOAD, invoice_out, payment_out

RECENT = 20
TIMELINE_LENGTH = 30


class CustomerOverview(BaseModel):
    customer: CustomerOut
    summary: SummaryOut  # the dashboard summary filtered to this customer, so the two always agree
    average_days_late: Decimal | None  # payment date minus due date, over every payment (negative = early)
    subscriptions: list[SubscriptionListItem]
    invoices: list[InvoiceOut]
    payments: list[PaymentOut]
    timeline: list[TimelineItem]


def customer_overview(
    db: Session, customer: Customer, out: CustomerOut, summary: SummaryOut
) -> CustomerOverview:
    payments = _payments(db, customer.id)
    invoices = _invoices(db, customer.id)
    return CustomerOverview(
        customer=out,
        summary=summary,
        average_days_late=_average_days_late(db, customer.id),
        subscriptions=_subscriptions(db, customer.id),
        invoices=[invoice_out(i) for i in invoices],
        payments=[payment_out(p) for p in payments],
        timeline=_timeline(db, customer.id, invoices, payments),
    )


def _subscriptions(db: Session, customer_id: int) -> list[SubscriptionListItem]:
    total = (
        select(func.coalesce(func.sum(SubscriptionLine.amount), 0))
        .where(SubscriptionLine.subscription_id == Subscription.id)
        .scalar_subquery()
    )
    rows = db.execute(
        select(Subscription, total)
        .where(Subscription.customer_id == customer_id)
        .options(joinedload(Subscription.customer), joinedload(Subscription.plan))
        .order_by(Subscription.id.desc())
        .limit(50)
    )
    return [
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


def _invoices(db: Session, customer_id: int) -> list[Invoice]:
    stmt = (
        select(Invoice)
        .where(Invoice.customer_id == customer_id)
        .options(*INVOICE_LOAD)
        .order_by(Invoice.id.desc())
        .limit(RECENT)
    )
    return list(db.scalars(stmt).unique())


def _payments(db: Session, customer_id: int) -> list[Payment]:
    stmt = (
        select(Payment)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .where(Invoice.customer_id == customer_id)
        .options(joinedload(Payment.invoice).joinedload(Invoice.customer), joinedload(Payment.recorded_by))
        .order_by(Payment.payment_date.desc(), Payment.id.desc())
        .limit(RECENT)
    )
    return list(db.scalars(stmt))


def _average_days_late(db: Session, customer_id: int) -> Decimal | None:
    days = Payment.payment_date - Invoice.due_date  # date - date is a whole number of days in PostgreSQL
    stmt = (
        select(cast(func.avg(days), Numeric(8, 1)))
        .select_from(Payment)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .where(Invoice.customer_id == customer_id)
    )
    return db.scalar(stmt)


def _day(value) -> str:
    return f"{value:%-d %b %Y}"  # 7 Oct 2026, as the screens show dates


def _invoice_name(invoice: Invoice) -> str:
    return invoice.number or f"Draft #{invoice.id}"


def _timeline(
    db: Session, customer_id: int, invoices: list[Invoice], payments: list[Payment]
) -> list[TimelineItem]:
    events = db.scalars(
        select(SubscriptionEvent)
        .join(Subscription, Subscription.id == SubscriptionEvent.subscription_id)
        .where(Subscription.customer_id == customer_id)
        .options(selectinload(SubscriptionEvent.subscription), selectinload(SubscriptionEvent.actor))
        .order_by(SubscriptionEvent.id.desc())
        .limit(TIMELINE_LENGTH)
    )
    items = [_event_item(e) for e in events]
    for invoice in invoices:
        link = f"/invoices/{invoice.id}"
        items.append(
            TimelineItem(
                at=invoice.created_at,
                kind="invoice",
                title=f"{_invoice_name(invoice)} created",
                detail=f"{_day(invoice.period_start)} to {_day(invoice.period_end)} · {invoice.subscription.number}",
                amount=invoice.total,
                link=link,
            )
        )
        if invoice.sent_at:
            items.append(
                TimelineItem(
                    at=invoice.sent_at, kind="invoice", title=f"{_invoice_name(invoice)} emailed", link=link
                )
            )
    for payment in payments:
        items.append(
            TimelineItem(
                at=payment.created_at,
                kind="payment",
                title=f"Payment received for {_invoice_name(payment.invoice)}",
                detail=f"{payment.method.replace('_', ' ').capitalize()} on {_day(payment.payment_date)}"
                + (f" · {payment.note}" if payment.note else ""),
                amount=payment.amount,
                link=f"/invoices/{payment.invoice_id}",
            )
        )
    items.sort(key=lambda item: item.at, reverse=True)
    return items[:TIMELINE_LENGTH]


def _event_item(event: SubscriptionEvent) -> TimelineItem:
    number = event.subscription.number
    if event.from_status is None:
        title = f"{number} created as a draft"
    elif event.from_status == event.to_status:
        title = f"{number}: {event.reason}" if event.reason else f"{number} updated"
    else:
        title = f"{number}: {event.from_status.lower()} → {event.to_status.lower()}"
    reason = event.reason if event.from_status != event.to_status else None
    by = event.actor.name if event.actor else "Daily job"
    return TimelineItem(
        at=event.created_at,
        kind="subscription",
        title=title,
        detail=" · ".join(x for x in (reason, by) if x),
        link=f"/subscriptions/{event.subscription_id}",
    )
