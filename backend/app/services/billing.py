"""Owner: A (steps A3, A4). Contract: never two live invoices for the same (subscription_id, period_start),
enforced by the DB unique index (cancelled invoices don't count); on IntegrityError, roll back and return the
existing invoice."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from itertools import count, takewhile

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import Conflict, Invalid, NotFound
from app.enums import AmountKind, DiscountScope, InvoiceStatus, SubscriptionStatus
from app.models import Discount, DiscountUsage, Invoice, InvoiceLine, Subscription, SubscriptionLine
from app.services.dates import add_period
from app.services.discounts import find_applicable_discounts
from app.services.pricing import (
    ZERO,
    DiscountRule,
    LineResult,
    TaxRule,
    compute_line,
    compute_totals,
    discount_for,
    round2,
)

# How many subscriptions one billing transaction handles before it commits and takes the next batch.
BILLING_BATCH_SIZE = 200

# ───────────────────────────── one invoice ─────────────────────────────


@dataclass
class ClaimedDiscounts:
    """The discounts this invoice actually won a use of (see `_claim_one_use`)."""

    product: Discount | None = None
    subscription: Discount | None = None

    def used(self) -> list[Discount]:
        return [d for d in (self.product, self.subscription) if d is not None]


def generate_invoice_for_period(db: Session, subscription_id: int, period_start: date) -> Invoice:
    """Creates the Draft invoice for one billing period of a subscription, in a single transaction:
    snapshot lines, apply discounts then taxes (services.pricing), record DiscountUsage and
    Discount.used_count, due_date = today + payment_term_days. The invoice number is assigned later,
    at Confirm. Idempotent: calling it twice for the same period returns the existing invoice."""
    existing = _find_invoice(db, subscription_id, period_start)
    if existing is not None:
        return existing

    sub = _load_billable_subscription(db, subscription_id)
    try:
        with db.begin_nested():
            return _create_invoice(db, sub, period_start)
    except IntegrityError:
        # Another worker billed this period first; the unique constraint kept us honest.
        winner = _find_invoice(db, subscription_id, period_start)
        if winner is None:
            raise
        return winner


def _find_invoice(db: Session, subscription_id: int, period_start: date) -> Invoice | None:
    """The live invoice for a period. A cancelled one has let go of its period, so it is not found."""
    return db.scalar(
        select(Invoice).where(
            Invoice.subscription_id == subscription_id,
            Invoice.period_start == period_start,
            Invoice.status != InvoiceStatus.CANCELLED,
        )
    )


def _load_billable_subscription(db: Session, subscription_id: int) -> Subscription:
    sub = db.scalar(
        select(Subscription)
        .where(Subscription.id == subscription_id)
        .options(
            selectinload(Subscription.plan),
            selectinload(Subscription.lines).joinedload(SubscriptionLine.product),
            selectinload(Subscription.lines).selectinload(SubscriptionLine.taxes),
        )
    )
    if sub is None:
        raise NotFound("Subscription not found.")
    if sub.status != SubscriptionStatus.ACTIVE:
        raise Invalid("Only active subscriptions can be billed.")
    if not sub.lines:
        raise Invalid("The subscription has no billable lines.")
    return sub


def _create_invoice(db: Session, sub: Subscription, period_start: date) -> Invoice:
    claimed = _claim_discounts(db, sub, period_start)
    priced = _price_lines(sub.lines, claimed)
    totals = compute_totals([result for _, result in priced])
    invoice = Invoice(
        number=None,
        subscription_id=sub.id,
        customer_id=sub.customer_id,
        period_start=period_start,
        period_end=add_period(period_start, sub.plan.billing_period) - timedelta(days=1),
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=sub.payment_term_days),
        subtotal=totals.subtotal,
        discount_total=totals.discount_total,
        tax_total=totals.tax_total,
        total=totals.total,
        amount_paid=ZERO,
        lines=[_invoice_line(line, result) for line, result in priced],
    )
    db.add(invoice)
    db.flush()
    db.add_all(DiscountUsage(discount_id=d.id, invoice_id=invoice.id) for d in claimed.used())
    db.flush()
    return invoice


# ───────────────────────────── discounts ─────────────────────────────


def _claim_discounts(db: Session, sub: Subscription, period_start: date) -> ClaimedDiscounts:
    available = find_applicable_discounts(db, sub.id, period_start)
    return ClaimedDiscounts(
        product=_claim_first(db, available, DiscountScope.PRODUCT),
        subscription=_claim_first(db, available, DiscountScope.SUBSCRIPTION),
    )


def _first_of_scope(discounts: list[Discount], scope: DiscountScope) -> Discount | None:
    return next((d for d in discounts if d.scope == scope), None)


def _claim_first(db: Session, discounts: list[Discount], scope: DiscountScope) -> Discount | None:
    first = _first_of_scope(discounts, scope)
    if first is None or not _claim_one_use(db, first):
        return None
    return first


def discount_reduction(lines: list[SubscriptionLine], discounts: list[Discount]) -> Decimal:
    """What the next invoice would take off these lines (before tax) with these applicable discounts, by the
    same rules as billing: at most one product discount and one subscription discount, never below zero.
    Nothing is claimed or saved, so reports can ask what the discounts are worth today."""
    chosen = ClaimedDiscounts(
        product=_first_of_scope(discounts, DiscountScope.PRODUCT),
        subscription=_first_of_scope(discounts, DiscountScope.SUBSCRIPTION),
    )
    return sum((result.discount_amount for _, result in _price_lines(lines, chosen)), ZERO)


def _claim_one_use(db: Session, discount: Discount) -> bool:
    """One atomic UPDATE: the row lock makes concurrent invoices queue up, so the limit can't be exceeded."""
    claimed_id = db.scalar(
        update(Discount)
        .where(
            Discount.id == discount.id,
            Discount.usage_limit.is_(None) | (Discount.used_count < Discount.usage_limit),
        )
        .values(used_count=Discount.used_count + 1)
        .returning(Discount.id)
    )
    return claimed_id is not None


# ───────────────────────────── pricing the lines ─────────────────────────────


def _price_lines(
    lines: list[SubscriptionLine], claimed: ClaimedDiscounts
) -> list[tuple[SubscriptionLine, LineResult]]:
    """Product discount first, then the subscription discount shared across the lines, then tax on what is
    left of each line. A discount never takes a line below zero."""
    product_discounts = [_product_discount(line, claimed.product) for line in lines]
    remaining = [_subtotal(line) - taken for line, taken in zip(lines, product_discounts, strict=True)]
    shares = _allocate(_subscription_discount(remaining, claimed.subscription), remaining)
    return [
        (line, _price_line(line, product_discount + share))
        for line, product_discount, share in zip(lines, product_discounts, shares, strict=True)
    ]


def _price_line(line: SubscriptionLine, discount_amount: Decimal) -> LineResult:
    return compute_line(
        line.unit_price,
        line.quantity,
        taxes=[TaxRule(t.kind, t.rate) for t in line.taxes if t.active],
        discount=DiscountRule(AmountKind.FIXED, discount_amount),
    )


def _subtotal(line: SubscriptionLine) -> Decimal:
    return round2(line.unit_price * line.quantity)


def _product_discount(line: SubscriptionLine, discount: Discount | None) -> Decimal:
    if discount is None or line.product_id not in {p.id for p in discount.products}:
        return ZERO
    return discount_for(_subtotal(line), DiscountRule(discount.kind, discount.value))


def _subscription_discount(remaining: list[Decimal], discount: Discount | None) -> Decimal:
    if discount is None:
        return ZERO
    return discount_for(sum(remaining, ZERO), DiscountRule(discount.kind, discount.value))


def _allocate(amount: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Splits `amount` in proportion to `weights`; the last share absorbs the rounding difference."""
    total_weight = sum(weights, ZERO)
    if amount == 0 or total_weight == 0:
        return [ZERO for _ in weights]
    shares = [round2(amount * weight / total_weight) for weight in weights]
    shares[-1] += amount - sum(shares, ZERO)
    return shares


def _invoice_line(line: SubscriptionLine, result: LineResult) -> InvoiceLine:
    """A snapshot: later catalogue edits don't change old invoices."""
    return InvoiceLine(
        product_id=line.product_id,
        description=line.product.name,
        quantity=line.quantity,
        unit_price=line.unit_price,
        discount_amount=result.discount_amount,
        tax_rate=_percent_rate(line),
        tax_amount=result.tax_amount,
        total=result.total,
    )


def _percent_rate(line: SubscriptionLine) -> Decimal:
    rates = (t.rate for t in line.taxes if t.active and t.kind == AmountKind.PERCENT)
    return sum(rates, ZERO)


# ───────────────────────────── the billing run ─────────────────────────────


@dataclass
class BillingRunResult:
    """`due = created + already_billed + skipped + failed` always holds."""

    as_of: date
    due: int = 0
    created: int = 0
    already_billed: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[dict] = field(default_factory=list)

    def record_failure(self, subscription_id: int, period_start: date, error: Exception, *, left_behind: int):
        """A failed period stays due and is retried on the next run, and so do the later periods
        of that subscription (they are `skipped`: not attempted, billed in order)."""
        self.failed += 1
        self.skipped += left_behind
        self.errors.append(
            {"subscription_id": subscription_id, "period_start": str(period_start), "error": str(error)}
        )


def run_billing(db: Session, as_of: date, *, batch_size: int = BILLING_BATCH_SIZE) -> BillingRunResult:
    """For every ACTIVE subscription with next_invoice_date <= as_of (and not past its expiry date): generate
    one invoice per due period (catch-up, so nothing is skipped) and advance next_invoice_date. Safe to run
    repeatedly.

    Subscriptions are taken in batches, each committed on its own, so a big run never holds one huge
    transaction or all its row locks at once. Batches walk forward by id, so each subscription is visited
    once per run: one that fails (or can't advance) stays due for the next run and can't make the loop spin."""
    result = BillingRunResult(as_of=as_of)
    last_id = 0
    while batch := _due_subscriptions(db, as_of, limit=batch_size, after_id=last_id):
        for sub in batch:
            _bill_subscription(db, sub, as_of, result)
        last_id = batch[-1].id
        db.commit()
    return result


def _due_subscriptions(db: Session, as_of: date, *, limit: int, after_id: int) -> list[Subscription]:
    """The next batch of due subscriptions after `after_id`. Locked with skip_locked so two simultaneous
    runs never take the same row. A subscription whose next period starts after its expiry date is no
    longer billed (renewing it moves the expiry date, and billing picks it up again)."""
    return list(
        db.scalars(
            select(Subscription)
            .where(
                Subscription.id > after_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.next_invoice_date.is_not(None),
                Subscription.next_invoice_date <= as_of,
                or_(
                    Subscription.expiry_date.is_(None),
                    Subscription.next_invoice_date <= Subscription.expiry_date,
                ),
            )
            .options(selectinload(Subscription.plan))
            .order_by(Subscription.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )


def _bill_subscription(db: Session, sub: Subscription, as_of: date, result: BillingRunResult) -> None:
    periods = _due_periods(sub, as_of)
    result.due += len(periods)
    for position, (index, period_start) in enumerate(periods):
        try:
            _bill_period(db, sub, index, period_start, result)
        except Exception as error:  # one bad subscription must not stop the whole billing day
            result.record_failure(sub.id, period_start, error, left_behind=len(periods) - position - 1)
            return


def _bill_period(
    db: Session, sub: Subscription, index: int, period_start: date, result: BillingRunResult
) -> None:
    already_billed = _find_invoice(db, sub.id, period_start) is not None
    with db.begin_nested():
        generate_invoice_for_period(db, sub.id, period_start)
        sub.next_invoice_date = add_period(sub.start_date, sub.plan.billing_period, index + 1)
        db.flush()
    if already_billed:
        result.already_billed += 1
    else:
        result.created += 1


def _due_periods(sub: Subscription, as_of: date) -> list[tuple[int, date]]:
    """(index, start date) of every period from `next_invoice_date` up to `as_of`. Each date is computed
    from the original start date, so a 31 Jan monthly subscription bills 28 Feb, 31 Mar, 30 Apr."""
    period = sub.plan.billing_period
    first = next(i for i in count() if add_period(sub.start_date, period, i) >= sub.next_invoice_date)
    starts = ((i, add_period(sub.start_date, period, i)) for i in count(first))
    last_day = (
        min(as_of, sub.expiry_date) if sub.expiry_date is not None else as_of
    )  # nothing starts after expiry
    return list(takewhile(lambda item: item[1] <= last_day, starts))


# ───────────────────────────── re-billing a cancelled invoice ─────────────────────────────


def rebill_invoice(db: Session, invoice_id: int) -> Invoice:
    """Bills a cancelled invoice's period again, as a new Draft. The billing run never does this by itself:
    a cancelled period stays unbilled until an admin asks. The cancelled invoice stays in the ledger, and
    the discount uses it held move to the new invoice instead of being counted twice."""
    old = db.scalar(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    if old is None:
        raise NotFound("Invoice not found.")
    if old.status != InvoiceStatus.CANCELLED:
        raise Conflict("Only a cancelled invoice can be billed again.")
    if _find_invoice(db, old.subscription_id, old.period_start) is not None:
        raise Conflict("This period has already been billed again.")

    with db.begin_nested():  # release the old uses and bill again as one step, or neither
        for usage in db.scalars(select(DiscountUsage).where(DiscountUsage.invoice_id == old.id)):
            db.execute(
                update(Discount)
                .where(Discount.id == usage.discount_id)
                .values(used_count=Discount.used_count - 1)
            )
            db.delete(usage)
        db.flush()
        return generate_invoice_for_period(db, old.subscription_id, old.period_start)
