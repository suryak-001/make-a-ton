"""Query conditions on invoices that more than one screen needs, so each rule is written once."""

from collections.abc import Callable
from datetime import date
from typing import Any

from sqlalchemy import ColumnElement

from app.enums import InvoiceStatus
from app.models import Invoice


def overdue_conditions(today: date | None = None) -> list:
    """Overdue is derived, not stored: Confirmed, past its due date, with a balance left (PRD FR-31)."""
    return [
        Invoice.status == InvoiceStatus.CONFIRMED,
        Invoice.due_date < (today or date.today()),
        Invoice.amount_paid < Invoice.total,
    ]


def present_conditions(*filters: tuple[Any, Callable[[Any], ColumnElement]]) -> list[ColumnElement]:
    """For each (value, build) pair whose filter value was given, `build(value)` is one SQL condition.
    Filters left out add nothing, so callers never branch on them."""
    return [build(value) for value, build in filters if value is not None]
