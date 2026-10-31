"""Owner: B — the subscription state machine, history, pricing of lines and the lifecycle job.

Contract with B: an ACTIVE subscription always has next_invoice_date, payment_term_days and at least
one line. next_invoice_date is always add_period(start_date, period, n) for some n, so month-end
subscriptions never drift. A PAUSED subscription is never ACTIVE, so it is never billed.

transition_subscription() is the ONLY place a status changes. Staff, the portal and the lifecycle job
all go through it, so the same plan-flag checks and the same SubscriptionEvent history apply everywhere.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import Conflict, Invalid, NotFound
from app.enums import AmountKind, BillingPeriod
from app.enums import SubscriptionStatus as S
from app.models import (
    Customer,
    Plan,
    Product,
    Subscription,
    SubscriptionEvent,
    SubscriptionLine,
    User,
)
from app.schemas.subscriptions import LineIn, SubscriptionIn
from app.services.dates import add_period
from app.services.pricing import TaxRule, compute_line
from app.services.sequence import next_number

# PAUSED is only reachable from ACTIVE (and only if plan.pausable); resuming returns to ACTIVE.
TRANSITIONS: dict[S, set[S]] = {
    S.DRAFT: {S.QUOTATION, S.CLOSED},
    S.QUOTATION: {S.CONFIRMED, S.DRAFT, S.CLOSED},
    S.CONFIRMED: {S.ACTIVE, S.CLOSED},
    S.ACTIVE: {S.PAUSED, S.CLOSED},
    S.PAUSED: {S.ACTIVE, S.CLOSED},
    S.CLOSED: set(),
}
EDITABLE = {S.DRAFT, S.QUOTATION}
LIVE = {S.ACTIVE, S.PAUSED}
# What a customer may do themselves in the portal (the plan flags still apply on top).
CUSTOMER_TARGETS = {S.PAUSED, S.ACTIVE, S.CLOSED}
RENEW = "RENEW"


# ───────────────────────────── rules ─────────────────────────────


def _blocker(sub: Subscription, to: S, plan: Plan, today: date) -> str | None:
    """Why `sub` can't move to `to` right now, or None if it can."""
    if to not in TRANSITIONS[sub.status]:
        return f"A {sub.status.lower()} subscription can't move to {to.lower()}."
    if to == S.PAUSED and not plan.pausable:
        return "This plan can't be paused."
    if to == S.PAUSED and sub.next_invoice_date is not None and sub.next_invoice_date < today:
        # Billing walks forward from next_invoice_date, so it can't both bill a period that started before
        # the pause and skip the ones inside it. If billing is behind, it has to catch up before pausing.
        return "Billing is behind for this subscription. It can be paused once the overdue invoice has been created."
    ended = sub.expiry_date is not None and sub.expiry_date < today
    if to == S.CLOSED and sub.status in LIVE and not plan.closable and not ended:
        return "This plan can't be closed early."
    if to == S.CONFIRMED and sub.quotation_valid_until and sub.quotation_valid_until < today:
        return "This quotation has expired."
    if to == S.ACTIVE and ended:
        return "This subscription has passed its expiry date. Renew it first."
    return None


def can_transition(sub: Subscription, to: S, plan: Plan, today: date | None = None) -> bool:
    return _blocker(sub, to, plan, today or date.today()) is None


def can_renew(sub: Subscription, plan: Plan) -> bool:
    return sub.status in LIVE and plan.renewable and sub.expiry_date is not None


def allowed_actions(
    sub: Subscription, plan: Plan, today: date | None = None, *, customer: bool = False
) -> list[str]:
    """Target statuses (and "RENEW") available now. `customer=True` limits it to portal self-service."""
    today = today or date.today()
    if customer and sub.status not in LIVE:
        return []
    targets = [
        t for t in S if can_transition(sub, t, plan, today) and (not customer or t in CUSTOMER_TARGETS)
    ]
    actions = [t.value for t in targets]
    if can_renew(sub, plan):
        actions.append(RENEW)
    return actions


def plan_is_available(plan: Plan, today: date) -> bool:
    return (
        plan.active
        and (plan.available_from is None or plan.available_from <= today)
        and (plan.available_to is None or plan.available_to >= today)
    )


# ───────────────────────────── history ─────────────────────────────


def _record(
    db: Session,
    sub: Subscription,
    from_status: S | None,
    to_status: S,
    actor: User | None,
    reason: str | None,
):
    db.add(
        SubscriptionEvent(
            subscription_id=sub.id,
            from_status=from_status,
            to_status=to_status,
            reason=reason or None,
            actor_id=actor.id if actor else None,
        )
    )


# ───────────────────────────── create / edit ─────────────────────────────


def _build_lines(db: Session, plan: Plan, lines_in: list[LineIn]) -> list[SubscriptionLine]:
    ids = {li.product_id for li in lines_in}
    products = {
        p.id: p
        for p in db.scalars(
            select(Product)
            .where(Product.id.in_(ids))
            .options(selectinload(Product.variants), selectinload(Product.default_taxes))
        )
    }
    lines = []
    for i, li in enumerate(lines_in):
        product = products.get(li.product_id)
        if product is None:
            raise Invalid("This product doesn't exist.", field=f"lines.{i}.product_id")
        if not product.active:
            raise Invalid("This product is inactive.", field=f"lines.{i}.product_id")
        variant = None
        if li.variant_id is not None:
            variant = next((v for v in product.variants if v.id == li.variant_id), None)
            if variant is None:
                raise Invalid("That variant doesn't belong to this product.", field=f"lines.{i}.variant_id")
        if li.quantity < plan.min_quantity:  # per line, enforced here on the server
            raise Invalid(
                f"Quantity must be at least {plan.min_quantity} on this plan.", field=f"lines.{i}.quantity"
            )

        taxes = [t for t in product.default_taxes if t.active]
        priced = compute_line(
            product.sales_price,
            li.quantity,
            variant.extra_price if variant else Decimal("0"),
            [TaxRule(AmountKind(t.kind), t.rate) for t in taxes],
        )
        lines.append(
            SubscriptionLine(
                product_id=product.id,
                variant_id=variant.id if variant else None,
                quantity=li.quantity,
                unit_price=priced.unit_price,  # snapshot: later price changes don't alter this subscription
                amount=priced.total,
                taxes=taxes,
            )
        )
    return lines


def _apply(
    db: Session, sub: Subscription, data: SubscriptionIn, today: date, *, check_plan_window: bool
) -> None:
    if db.get(Customer, data.customer_id) is None:
        raise Invalid("This customer doesn't exist.", field="customer_id")
    plan = db.get(Plan, data.plan_id)
    if plan is None:
        raise Invalid("This plan doesn't exist.", field="plan_id")
    if check_plan_window and not plan_is_available(plan, today):
        raise Invalid("This plan isn't available for new subscriptions right now.", field="plan_id")
    if data.expiry_date is not None and data.expiry_date < data.start_date:
        raise Invalid("The expiry date can't be before the start date.", field="expiry_date")

    new_lines = _build_lines(db, plan, data.lines)

    sub.customer_id, sub.plan_id = data.customer_id, data.plan_id
    sub.start_date, sub.expiry_date = data.start_date, data.expiry_date
    sub.payment_term_days, sub.validity_days, sub.notes = (
        data.payment_term_days,
        data.validity_days,
        data.notes,
    )
    if sub.status == S.DRAFT:
        # Provisional expiry so a fresh quote shows one; it is recomputed from the day the quote is SENT.
        sub.quotation_valid_until = today + timedelta(days=data.validity_days)
    sub.lines.clear()
    sub.lines.extend(new_lines)


def create_subscription(
    db: Session, data: SubscriptionIn, actor: User | None, today: date | None = None
) -> Subscription:
    today = today or date.today()
    sub = Subscription(
        number=next_number(db, "SUB", "SUB-"), status=S.DRAFT, created_by_id=actor.id if actor else None
    )
    _apply(db, sub, data, today, check_plan_window=True)
    db.add(sub)
    db.flush()
    _record(db, sub, None, S.DRAFT, actor, None)
    db.flush()
    return sub


def update_subscription(
    db: Session, subscription_id: int, data: SubscriptionIn, today: date | None = None
) -> Subscription:
    today = today or date.today()
    sub = _locked(db, subscription_id)
    if sub.status not in EDITABLE:
        raise Conflict("Only draft and quotation subscriptions can be edited.")
    _apply(db, sub, data, today, check_plan_window=data.plan_id != sub.plan_id)
    db.flush()
    return sub


def delete_subscription(db: Session, subscription_id: int) -> None:
    sub = _locked(db, subscription_id)
    if sub.status != S.DRAFT:
        raise Conflict("Only a draft can be deleted. Close the subscription instead.")
    db.delete(sub)
    db.flush()


# ───────────────────────────── state machine ─────────────────────────────


def _locked(db: Session, subscription_id: int) -> Subscription:
    sub = db.scalar(select(Subscription).where(Subscription.id == subscription_id).with_for_update())
    if sub is None:
        raise NotFound("Subscription not found")
    return sub


def _skip_paused_periods(sub: Subscription, today: date) -> None:
    """On resume, periods that fell inside the pause are never billed: move next_invoice_date to the first
    period start that is not in the past. (Pausing is blocked while billing is behind, so everything being
    skipped started on or after the day the subscription was paused.) Stays on the add_period(start_date, period, n) grid."""
    if sub.next_invoice_date is None:
        return
    period: BillingPeriod = sub.plan.billing_period
    n = 0
    while add_period(sub.start_date, period, n) < sub.next_invoice_date:
        n += 1
    due = add_period(sub.start_date, period, n)
    while due < today:
        n += 1
        due = add_period(sub.start_date, period, n)
    sub.next_invoice_date = due


def transition_subscription(
    db: Session,
    subscription_id: int,
    to: S,
    *,
    actor: User | None = None,
    reason: str | None = None,
    today: date | None = None,
) -> Subscription:
    """Moves a subscription to `to`, enforcing the state machine and the plan's flags, and records a
    SubscriptionEvent. On -> ACTIVE (first time) next_invoice_date = start_date; on resume it skips the
    paused periods. Raises Conflict when the move isn't allowed."""
    today = today or date.today()
    sub = _locked(db, subscription_id)
    problem = _blocker(sub, to, sub.plan, today)
    if problem:
        raise Conflict(problem)

    previous = sub.status
    if to == S.QUOTATION:
        sub.quotation_valid_until = today + timedelta(
            days=sub.validity_days
        )  # the clock starts when it is sent
    elif to == S.ACTIVE:
        if previous == S.CONFIRMED:
            sub.next_invoice_date = sub.start_date
        else:  # resume
            _skip_paused_periods(sub, today)
    elif to == S.CLOSED:
        sub.next_invoice_date = None

    sub.status = to
    _record(db, sub, previous, to, actor, reason)
    db.flush()
    return sub


def renew_subscription(
    db: Session, subscription_id: int, *, actor: User | None = None, reason: str | None = None
) -> Subscription:
    """Extends the expiry date by one billing period of the plan (before or after it has passed)."""
    sub = _locked(db, subscription_id)
    if not can_renew(sub, sub.plan):
        raise Conflict("This subscription can't be renewed.")
    old = sub.expiry_date
    sub.expiry_date = add_period(old, sub.plan.billing_period)
    _record(db, sub, sub.status, sub.status, actor, reason or f"Renewed: expiry {old} → {sub.expiry_date}")
    db.flush()
    return sub


def customer_transition(
    db: Session, user: User, subscription_id: int, to: S, reason: str | None = None
) -> Subscription:
    """Portal self-service: same rules as staff, plus ownership (404 for anyone else's) and the
    customer-only action set. Goes through transition_subscription."""
    sub = _own_subscription(db, user, subscription_id)
    if sub.status not in LIVE or to not in CUSTOMER_TARGETS:
        raise Conflict("That isn't available for this subscription.")
    return transition_subscription(db, sub.id, to, actor=user, reason=reason)


def customer_renew(db: Session, user: User, subscription_id: int, reason: str | None = None) -> Subscription:
    sub = _own_subscription(db, user, subscription_id)
    return renew_subscription(db, sub.id, actor=user, reason=reason)


def _own_subscription(db: Session, user: User, subscription_id: int) -> Subscription:
    """The customer's own, non-draft subscription, or NotFound (never leak that another one exists)."""
    sub = db.get(Subscription, subscription_id)
    if sub is None or user.customer is None or sub.customer_id != user.customer.id or sub.status == S.DRAFT:
        raise NotFound("Subscription not found")
    return sub


# ───────────────────────────── lifecycle job ─────────────────────────────


def run_lifecycle_job(db: Session, as_of: date | None = None) -> dict[str, int]:
    """Daily job. Idempotent. Closes live subscriptions on plans with auto_close once they are past
    their expiry date, and expires quotations past their validity. Run billing first so a final
    period is invoiced before the subscription closes."""
    as_of = as_of or date.today()
    ended = list(
        db.scalars(
            select(Subscription)
            .join(Plan)
            .where(
                Subscription.status.in_(LIVE),
                Plan.auto_close.is_(True),
                Subscription.expiry_date < as_of,
            )
            .with_for_update(of=Subscription)
        )
    )
    stale = list(
        db.scalars(
            select(Subscription)
            .where(Subscription.status == S.QUOTATION, Subscription.quotation_valid_until < as_of)
            .with_for_update()
        )
    )
    for sub, why in [(s, "Plan ended") for s in ended] + [(s, "Quotation expired") for s in stale]:
        previous = sub.status
        sub.status = S.CLOSED
        sub.next_invoice_date = None
        _record(db, sub, previous, S.CLOSED, None, why)
    db.flush()
    return {"closed": len(ended), "expired_quotations": len(stale)}
