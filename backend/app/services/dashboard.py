"""What each role sees first. The admin gets proof the numbers are sound (aging, counts, no double billing) and the
next setup step; staff get a work queue of things to do today; a customer gets their own account at a glance.
Everything is a database aggregate or a short, limited list."""

from datetime import date, timedelta
from decimal import Decimal
from time import perf_counter

from pydantic import BaseModel
from sqlalchemy import Numeric, case, cast, exists, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import Conflict, Invalid
from app.enums import InvoiceStatus, SubscriptionStatus
from app.models import Customer, Invoice, InvoiceReminder, Payment, Plan, Product, Subscription
from app.schemas.money import InvoiceOut
from app.services.invoice_queries import overdue_conditions
from app.services.mail import send_mail
from app.services.money_views import INVOICE_LOAD, invoice_out
from app.services.subscriptions import allowed_actions

ZERO = Decimal("0.00")
LIST_LIMIT = 10
RENEWAL_WINDOW_DAYS = 14
QUOTE_WINDOW_DAYS = 7

# (key, label, first day overdue, last day overdue). "current" is not due yet.
AGING = (
    ("current", "Current"),
    ("1-30", "1–30 days"),
    ("31-60", "31–60 days"),
    ("61-90", "61–90 days"),
    ("90+", "90+ days"),
)


def stage_for(due_date: date, today: date) -> str:
    days = (today - due_date).days
    if days <= 0:
        return "current"
    if days <= 30:
        return "1-30"
    if days <= 60:
        return "31-60"
    if days <= 90:
        return "61-90"
    return "90+"


def _owed():
    return cast(func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0), Numeric(12, 2))


# ───────────────────────────── admin: aging, proof, setup ─────────────────────────────


class AgingBucket(BaseModel):
    key: str
    label: str
    count: int
    amount: Decimal


def aging(db: Session, today: date | None = None) -> list[AgingBucket]:
    """Confirmed invoices with a balance, bucketed by how long past due, in one grouped query."""
    today = today or date.today()
    bucket = case(
        (Invoice.due_date >= today, "current"),
        (Invoice.due_date >= today - timedelta(days=30), "1-30"),
        (Invoice.due_date >= today - timedelta(days=60), "31-60"),
        (Invoice.due_date >= today - timedelta(days=90), "61-90"),
        else_="90+",
    )
    stmt = (
        select(bucket, func.count(), _owed())
        .where(Invoice.status == InvoiceStatus.CONFIRMED, Invoice.amount_paid < Invoice.total)
        .group_by(bucket)
    )
    found = {key: (count, amount) for key, count, amount in db.execute(stmt)}
    return [
        AgingBucket(key=k, label=label, count=found.get(k, (0, ZERO))[0], amount=found.get(k, (0, ZERO))[1])
        for k, label in AGING
    ]


class Proof(BaseModel):
    subscriptions: int
    invoices: int
    payments: int
    customers: int
    duplicate_invoice_periods: int  # subscriptions billed twice for one period; must always be 0
    last_invoice_at: str | None
    measured_ms: int  # how long these checks took, so the speed claim is a measurement


def proof(db: Session) -> Proof:
    started = perf_counter()
    subscriptions = db.scalar(select(func.count()).select_from(Subscription)) or 0
    invoices = db.scalar(select(func.count()).select_from(Invoice)) or 0
    payments = db.scalar(select(func.count()).select_from(Payment)) or 0
    customers = db.scalar(select(func.count()).select_from(Customer)) or 0
    twice = (
        select(Invoice.subscription_id)
        .where(Invoice.status != InvoiceStatus.CANCELLED)
        .group_by(Invoice.subscription_id, Invoice.period_start)
        .having(func.count() > 1)
        .subquery()
    )
    duplicates = db.scalar(select(func.count()).select_from(twice)) or 0
    last = db.scalar(select(func.max(Invoice.created_at)))
    aging(db)
    return Proof(
        subscriptions=subscriptions,
        invoices=invoices,
        payments=payments,
        customers=customers,
        duplicate_invoice_periods=duplicates,
        last_invoice_at=last.isoformat() if last else None,
        measured_ms=round((perf_counter() - started) * 1000),
    )


class SetupStep(BaseModel):
    key: str
    title: str
    cta: str
    href: str
    done: bool


def setup_steps(db: Session) -> list[SetupStep]:
    """The first-run path through the product. The first step not done is what the banner points at; it follows real
    data, so it moves on by itself and disappears once everything is done."""

    def has(model, *conditions) -> bool:
        return bool(db.scalar(select(exists(select(1).select_from(model).where(*conditions)))))

    return [
        SetupStep(
            key="product",
            title="Add a product to sell",
            cta="Add a product",
            href="/products",
            done=has(Product),
        ),
        SetupStep(
            key="plan",
            title="Create a plan with a billing period",
            cta="Create a plan",
            href="/plans",
            done=has(Plan),
        ),
        SetupStep(
            key="subscription",
            title="Start a subscription for a customer",
            cta="New subscription",
            href="/subscriptions",
            done=has(Subscription, Subscription.status == SubscriptionStatus.ACTIVE),
        ),
        SetupStep(
            key="billing",
            title="Run billing to create the first invoices",
            cta="Open billing run",
            href="/billing-run",
            done=has(Invoice),
        ),
        SetupStep(
            key="payment",
            title="Record a payment against an invoice",
            cta="Record payment",
            href="/payments",
            done=has(Payment),
        ),
    ]


# ───────────────────────────── staff: the work queue ─────────────────────────────


class RenewalDue(BaseModel):
    id: int
    number: str
    customer: str
    plan: str
    expiry_date: date
    days_left: int
    renewable: bool
    auto_close: bool


class QuoteExpiring(BaseModel):
    id: int
    number: str
    customer: str
    valid_until: date
    days_left: int


class ToChase(BaseModel):
    id: int
    number: str | None
    customer: str
    due_date: date
    days_overdue: int
    outstanding: Decimal
    stage: str
    reminded: bool  # the reminder for this stage has already gone out
    last_reminder_at: str | None


class WorkQueue(BaseModel):
    draft_invoices: int
    overdue_invoices: int
    renewals_due: list[RenewalDue]
    quotes_expiring: list[QuoteExpiring]
    to_chase: list[ToChase]


def work_queue(db: Session, today: date | None = None) -> WorkQueue:
    today = today or date.today()
    renewals = db.scalars(
        select(Subscription)
        .where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.expiry_date.is_not(None),
            Subscription.expiry_date.between(today, today + timedelta(days=RENEWAL_WINDOW_DAYS)),
        )
        .options(selectinload(Subscription.customer), selectinload(Subscription.plan))
        .order_by(Subscription.expiry_date)
        .limit(LIST_LIMIT)
    ).all()
    quotes = db.scalars(
        select(Subscription)
        .where(
            Subscription.status == SubscriptionStatus.QUOTATION,
            Subscription.quotation_valid_until.between(today, today + timedelta(days=QUOTE_WINDOW_DAYS)),
        )
        .options(selectinload(Subscription.customer))
        .order_by(Subscription.quotation_valid_until)
        .limit(LIST_LIMIT)
    ).all()
    overdue = db.scalars(
        select(Invoice)
        .where(*overdue_conditions(today))
        .options(selectinload(Invoice.customer))
        .order_by(Invoice.due_date)
        .limit(LIST_LIMIT)
    ).all()
    reminders: dict[tuple[int, str], str] = {}
    if overdue:
        for r in db.scalars(
            select(InvoiceReminder).where(InvoiceReminder.invoice_id.in_([i.id for i in overdue]))
        ):
            reminders[(r.invoice_id, r.stage)] = r.sent_at.isoformat()
    return WorkQueue(
        draft_invoices=db.scalar(
            select(func.count()).select_from(Invoice).where(Invoice.status == InvoiceStatus.DRAFT)
        )
        or 0,
        overdue_invoices=db.scalar(
            select(func.count()).select_from(Invoice).where(*overdue_conditions(today))
        )
        or 0,
        renewals_due=[
            RenewalDue(
                id=s.id,
                number=s.number,
                customer=s.customer.name,
                plan=s.plan.name,
                expiry_date=s.expiry_date,
                days_left=(s.expiry_date - today).days,
                renewable=s.plan.renewable,
                auto_close=s.plan.auto_close,
            )
            for s in renewals
        ],
        quotes_expiring=[
            QuoteExpiring(
                id=s.id,
                number=s.number,
                customer=s.customer.name,
                valid_until=s.quotation_valid_until,
                days_left=(s.quotation_valid_until - today).days,
            )
            for s in quotes
        ],
        to_chase=[
            ToChase(
                id=i.id,
                number=i.number,
                customer=i.customer.name,
                due_date=i.due_date,
                days_overdue=(today - i.due_date).days,
                outstanding=i.total - i.amount_paid,
                stage=(stage := stage_for(i.due_date, today)),
                reminded=(i.id, stage) in reminders,
                last_reminder_at=reminders.get((i.id, stage)),
            )
            for i in overdue
        ],
    )


def remind(db: Session, invoice: Invoice, user_id: int, today: date | None = None) -> str:
    """Chases one overdue invoice by email. One reminder per invoice per aging stage: the unique row is the guard, so
    two people clicking at once send one email. The row is written before the email goes out and committed after, so a
    mail failure leaves nothing recorded and the reminder can be retried."""
    today = today or date.today()
    if not (
        invoice.status == InvoiceStatus.CONFIRMED
        and invoice.due_date < today
        and invoice.amount_paid < invoice.total
    ):
        raise Invalid("Only an overdue invoice can be chased.")
    stage = stage_for(invoice.due_date, today)
    already = db.scalar(
        select(exists().where(InvoiceReminder.invoice_id == invoice.id, InvoiceReminder.stage == stage))
    )
    if already:
        raise Conflict("A reminder for this stage has already been sent.")
    db.add(InvoiceReminder(invoice_id=invoice.id, stage=stage, sent_by_id=user_id))
    db.flush()
    owed = invoice.total - invoice.amount_paid
    send_mail(
        invoice.customer.email,
        f"Reminder: invoice {invoice.number} is overdue",
        f"Hello {invoice.customer.name},\n\nInvoice {invoice.number} was due on {invoice.due_date} and {owed} is still "
        f"outstanding. You can pay it from the customer portal.\n\nThank you.",
    )
    return stage


# ───────────────────────────── customer: their account at a glance ─────────────────────────────


class PortalAlert(BaseModel):
    kind: str  # danger | warning | success
    text: str
    href: str | None = None


class PortalSub(BaseModel):
    id: int
    number: str
    status: SubscriptionStatus
    plan: str
    billing_period: str
    total: Decimal
    next_invoice_date: date | None
    expiry_date: date | None
    allowed_actions: list[str]


class PortalHome(BaseModel):
    name: str
    outstanding: Decimal
    overdue_count: int
    overdue_amount: Decimal
    next_due: InvoiceOut | None
    alerts: list[PortalAlert]
    subscriptions: list[PortalSub]
    recent_invoices: list[InvoiceOut]


def portal_home(db: Session, customer: Customer, today: date | None = None) -> PortalHome:
    """Everything is scoped to `customer`; the router passes only the signed-in customer's own record."""
    today = today or date.today()
    live = (SubscriptionStatus.CONFIRMED, SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED)
    subs = db.scalars(
        select(Subscription)
        .where(Subscription.customer_id == customer.id, Subscription.status.in_(live))
        .options(selectinload(Subscription.lines), selectinload(Subscription.plan))
        .order_by(Subscription.id.desc())
    ).all()
    open_invoices = (
        db.scalars(
            select(Invoice)
            .where(
                Invoice.customer_id == customer.id,
                Invoice.status == InvoiceStatus.CONFIRMED,
                Invoice.amount_paid < Invoice.total,
            )
            .options(*INVOICE_LOAD)
            .order_by(Invoice.due_date)
        )
        .unique()
        .all()
    )
    recent = (
        db.scalars(
            select(Invoice)
            .where(
                Invoice.customer_id == customer.id,
                Invoice.status != InvoiceStatus.DRAFT,
                Invoice.number.is_not(None),
            )
            .options(*INVOICE_LOAD)
            .order_by(Invoice.id.desc())
            .limit(5)
        )
        .unique()
        .all()
    )

    overdue = [i for i in open_invoices if i.due_date < today]
    owed = sum((i.total - i.amount_paid for i in open_invoices), ZERO)
    overdue_owed = sum((i.total - i.amount_paid for i in overdue), ZERO)
    alerts: list[PortalAlert] = []
    if overdue:
        n = len(overdue)
        alerts.append(
            PortalAlert(
                kind="danger",
                text=f"{n} invoice{'s' if n != 1 else ''} overdue, ₹{overdue_owed:,.2f} to pay",
                href=f"/portal/invoices/{overdue[0].id}",
            )
        )
    for s in subs:
        if (
            s.status == SubscriptionStatus.ACTIVE
            and s.expiry_date
            and 0 <= (s.expiry_date - today).days <= RENEWAL_WINDOW_DAYS
        ):
            days = (s.expiry_date - today).days
            alerts.append(
                PortalAlert(
                    kind="warning",
                    text=f"{s.number} ends {'today' if days == 0 else f'in {days} day' + ('s' if days != 1 else '')}",
                    href=f"/portal/subscriptions/{s.id}",
                )
            )
    if not alerts and subs:
        alerts.append(PortalAlert(kind="success", text="You’re all paid up. Nothing needs your attention."))
    return PortalHome(
        name=customer.name,
        outstanding=owed,
        overdue_count=len(overdue),
        overdue_amount=overdue_owed,
        next_due=invoice_out(open_invoices[0], today) if open_invoices else None,
        alerts=alerts,
        subscriptions=[
            PortalSub(
                id=s.id,
                number=s.number,
                status=s.status,
                plan=s.plan.name,
                billing_period=s.plan.billing_period,
                total=sum((line.amount for line in s.lines), ZERO),
                next_invoice_date=s.next_invoice_date,
                expiry_date=s.expiry_date,
                allowed_actions=allowed_actions(s, s.plan, today, customer=True),
            )
            for s in subs
        ],
        recent_invoices=[invoice_out(i, today) for i in recent],
    )
