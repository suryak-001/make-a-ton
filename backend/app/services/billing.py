"""Owner: B (steps B4, B5). Contract: never two invoices for the same (subscription_id, period_start),
enforced by the DB unique constraint; on IntegrityError, roll back and return the existing invoice."""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.models import Invoice


def generate_invoice_for_period(db: Session, subscription_id: int, period_start: date) -> Invoice:
    """Creates the invoice for one billing period of a subscription, in a single transaction:
    snapshot lines → apply taxes + applicable discounts (services.pricing) → record DiscountUsage and
    increment Discount.used_count → number via next_number(db, f"INV-{year}", ...) →
    due_date = invoice_date + payment_term_days. Idempotent: calling it twice for the same period
    returns the existing invoice."""
    raise NotImplementedError("TODO(B4): generate_invoice_for_period")


@dataclass
class BillingRunResult:
    created: int = 0
    skipped: int = 0
    errors: list[dict] = field(default_factory=list)


def run_billing(db: Session, as_of: date) -> BillingRunResult:
    """For every ACTIVE subscription with next_invoice_date <= as_of: generate one invoice per due
    period (catch-up, so nothing is skipped) and advance next_invoice_date with add_period().
    Safe to run repeatedly."""
    raise NotImplementedError("TODO(B5): run_billing")
