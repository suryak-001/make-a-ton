"""Owner: A (steps A7, A8). Contract: an ACTIVE subscription always has next_invoice_date,
payment_term_days and at least one line — B's billing run relies on that."""

from datetime import date

from sqlalchemy.orm import Session

from app.enums import SubscriptionStatus as S
from app.models import Plan, Subscription

TRANSITIONS: dict[S, set[S]] = {
    S.DRAFT: {S.QUOTATION, S.CLOSED},
    S.QUOTATION: {S.CONFIRMED, S.DRAFT, S.CLOSED},
    S.CONFIRMED: {S.ACTIVE, S.CLOSED},
    S.ACTIVE: {S.PAUSED, S.CLOSED},  # PAUSED only if plan.pausable; early CLOSED only if plan.closable
    S.PAUSED: {S.ACTIVE, S.CLOSED},
    S.CLOSED: set(),
}


def can_transition(current: S, to: S, plan: Plan) -> bool:
    if to not in TRANSITIONS[current]:
        return False
    if to == S.PAUSED and not plan.pausable:
        return False
    if to == S.CLOSED and current == S.ACTIVE and not plan.closable:
        return False
    return True


def transition_subscription(db: Session, subscription_id: int, to: S) -> Subscription:
    """Moves a subscription to a new status, enforcing can_transition.
    On → ACTIVE: set next_invoice_date = start_date (if not already set)."""
    raise NotImplementedError("TODO(A7): transition_subscription")


def run_lifecycle_job(db: Session, as_of: date) -> dict[str, int]:
    """Daily job (A8): close expired subs whose plan.auto_close is on, expire stale quotations. Idempotent."""
    raise NotImplementedError("TODO(A8): run_lifecycle_job")
