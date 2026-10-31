"""Owner: B (step B3)."""

from datetime import date

from sqlalchemy.orm import Session

from app.models import Discount


def find_applicable_discounts(db: Session, subscription_id: int, as_of: date) -> list[Discount]:
    """Discounts that apply to a subscription on a given date: active, within start/end dates,
    used_count < usage_limit, min purchase / min quantity met, and scoped to the subscription itself
    (SUBSCRIPTION) or to products on its lines (PRODUCT)."""
    raise NotImplementedError("TODO(B3): find_applicable_discounts")
