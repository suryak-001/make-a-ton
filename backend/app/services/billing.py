"""Owner: A (steps A3, A4). Contract: never two invoices for the same (subscription_id, period_start),
enforced by the DB unique constraint; on IntegrityError, roll back and return the existing invoice."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import Invalid, NotFound
from app.enums import AmountKind, DiscountScope, SubscriptionStatus
from app.models import Discount, DiscountUsage, Invoice, InvoiceLine, Subscription, SubscriptionLine
from app.services.dates import add_period
from app.services.discounts import find_applicable_discounts
from app.services.pricing import DiscountRule, TaxRule, compute_line, round2


def generate_invoice_for_period(db: Session, subscription_id: int, period_start: date) -> Invoice:
    """Creates the invoice for one billing period of a subscription, in a single transaction:
    snapshot lines → apply taxes + applicable discounts (services.pricing) → record DiscountUsage and
    increment Discount.used_count → number via next_number(db, f"INV-{year}", ...) →
    due_date = invoice_date + payment_term_days. Idempotent: calling it twice for the same period
    returns the existing invoice."""
    existing = db.scalar(
        select(Invoice).where(
            Invoice.subscription_id == subscription_id, Invoice.period_start == period_start
        )
    )
    if existing is not None:
        return existing

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

    discounts = find_applicable_discounts(db, sub.id, period_start)
    product_discount = next((d for d in discounts if d.scope == DiscountScope.PRODUCT), None)
    subscription_discount = next((d for d in discounts if d.scope == DiscountScope.SUBSCRIPTION), None)

    def claim(discount: Discount | None) -> bool:
        if discount is None:
            return False
        claimed = db.scalar(
            update(Discount)
            .where(
                Discount.id == discount.id,
                (Discount.usage_limit.is_(None) | (Discount.used_count < Discount.usage_limit)),
            )
            .values(used_count=Discount.used_count + 1)
            .returning(Discount.id)
        )
        return claimed is not None

    product_ids = {p.id for p in product_discount.products} if product_discount else set()
    product_applies = product_discount is not None and any(
        line.product_id in product_ids for line in sub.lines
    )

    try:
        with db.begin_nested():
            # The claim and invoice share this savepoint: a duplicate/race rolls the usage count back too.
            product_claimed = claim(product_discount) if product_applies else False
            subscription_claimed = claim(subscription_discount)
            next_start = add_period(period_start, sub.plan.billing_period)
            invoice = Invoice(
                number=None,
                subscription_id=sub.id,
                customer_id=sub.customer_id,
                period_start=period_start,
                period_end=next_start - timedelta(days=1),
                invoice_date=date.today(),
                due_date=date.today() + timedelta(days=sub.payment_term_days),
                subtotal=Decimal("0"),
                discount_total=Decimal("0"),
                tax_total=Decimal("0"),
                total=Decimal("0"),
                amount_paid=Decimal("0"),
            )
            db.add(invoice)
            db.flush()

            subtotal = discount_total = tax_total = total = Decimal("0")
            for line in sub.lines:
                chosen = product_discount if product_claimed and line.product_id in product_ids else None
                taxes = [TaxRule(t.kind, t.rate) for t in line.taxes if t.active]
                priced = compute_line(
                    line.unit_price,
                    line.quantity,
                    taxes=taxes,
                    discount=DiscountRule(chosen.kind, chosen.value) if chosen else None,
                )
                percent_rate = sum(
                    (t.rate for t in line.taxes if t.active and t.kind == AmountKind.PERCENT),
                    start=Decimal("0"),
                )
                invoice.lines.append(
                    InvoiceLine(
                        product_id=line.product_id,
                        description=line.product.name,
                        quantity=line.quantity,
                        unit_price=line.unit_price,
                        discount_amount=priced.discount_amount,
                        tax_rate=percent_rate,
                        tax_amount=priced.tax_amount,
                        total=priced.total,
                    )
                )
                subtotal += priced.subtotal
                discount_total += priced.discount_amount
                tax_total += priced.tax_amount
                total += priced.total

            if subscription_claimed and subscription_discount is not None:
                eligible = round2(subtotal - discount_total)
                raw = (
                    eligible * subscription_discount.value / 100
                    if subscription_discount.kind == AmountKind.PERCENT
                    else subscription_discount.value
                )
                extra = min(round2(raw), eligible)
                discount_total += extra
                total -= extra
                invoice.lines.append(
                    InvoiceLine(
                        product_id=None,
                        description=f"Discount: {subscription_discount.name}",
                        quantity=1,
                        unit_price=-extra,
                        discount_amount=extra,
                        tax_rate=Decimal("0"),
                        tax_amount=Decimal("0"),
                        total=-extra,
                    )
                )

            invoice.subtotal = round2(subtotal)
            invoice.discount_total = round2(discount_total)
            invoice.tax_total = round2(tax_total)
            invoice.total = round2(max(total, Decimal("0")))
            for discount, claimed in (
                (product_discount, product_claimed),
                (subscription_discount, subscription_claimed),
            ):
                if discount is not None and claimed:
                    db.add(DiscountUsage(discount_id=discount.id, invoice_id=invoice.id))
            db.flush()
            return invoice
    except IntegrityError:
        existing = db.scalar(
            select(Invoice).where(
                Invoice.subscription_id == subscription_id, Invoice.period_start == period_start
            )
        )
        if existing is not None:
            return existing
        raise


@dataclass
class BillingRunResult:
    created: int = 0
    skipped: int = 0
    errors: list[dict] = field(default_factory=list)


def run_billing(db: Session, as_of: date) -> BillingRunResult:
    """For every ACTIVE subscription with next_invoice_date <= as_of: generate one invoice per due
    period (catch-up, so nothing is skipped) and advance next_invoice_date with add_period().
    Safe to run repeatedly."""
    result = BillingRunResult()
    due = list(
        db.scalars(
            select(Subscription)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.next_invoice_date.is_not(None),
                Subscription.next_invoice_date <= as_of,
            )
            .options(selectinload(Subscription.plan))
            .order_by(Subscription.id)
            .with_for_update(skip_locked=True)
        )
    )
    for sub in due:
        # Re-anchor every period to the original start date to avoid Jan-31 -> Feb-28 -> Mar-28 drift.
        index = 0
        while add_period(sub.start_date, sub.plan.billing_period, index) < sub.next_invoice_date:
            index += 1
        while sub.next_invoice_date <= as_of:
            period_start = sub.next_invoice_date
            try:
                with db.begin_nested():
                    before = db.scalar(
                        select(Invoice.id).where(
                            Invoice.subscription_id == sub.id, Invoice.period_start == period_start
                        )
                    )
                    generate_invoice_for_period(db, sub.id, period_start)
                    result.skipped += int(before is not None)
                    result.created += int(before is None)
                    index += 1
                    sub.next_invoice_date = add_period(sub.start_date, sub.plan.billing_period, index)
                    db.flush()
            except Exception as exc:  # one bad subscription must not stop the whole billing day
                result.errors.append(
                    {"subscription_id": sub.id, "period_start": str(period_start), "error": str(exc)}
                )
                break
    return result
