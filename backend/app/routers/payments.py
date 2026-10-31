"""Payments recorded against confirmed invoices."""

from datetime import date

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.csv_export import csv_response
from app.core.deps import Db, StaffUser
from app.core.pagination import Page, Pages, paginate
from app.enums import PaymentMethod
from app.models import Invoice, Payment
from app.schemas.money import PaymentIn, PaymentOut
from app.services.invoice_queries import present_conditions
from app.services.money_views import payment_out
from app.services.payments import record_payment

router = APIRouter(prefix="/api/payments", tags=["payments"])

_LOAD = (joinedload(Payment.invoice).joinedload(Invoice.customer), joinedload(Payment.recorded_by))


def _conditions(
    invoice_id: int | None, method: PaymentMethod | None, from_date: date | None, to_date: date | None
) -> list:
    return present_conditions(
        (invoice_id, lambda v: Payment.invoice_id == v),
        (method, lambda v: Payment.method == v),
        (from_date, lambda v: Payment.payment_date >= v),
        (to_date, lambda v: Payment.payment_date <= v),
    )


@router.get("", response_model=Page[PaymentOut])
def list_payments(
    db: Db,
    _: StaffUser,
    pages: Pages,
    invoice_id: int | None = None,
    method: PaymentMethod | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
):
    stmt = (
        select(Payment)
        .where(*_conditions(invoice_id, method, from_date, to_date))
        .options(*_LOAD)
        .order_by(Payment.payment_date.desc(), Payment.id.desc())
    )
    rows, total = paginate(db, stmt, pages)
    return Page(items=[payment_out(p) for p in rows], total=total, page=pages.page, page_size=pages.page_size)


@router.get("/export.csv")
def export_payments(
    db: Db,
    _: StaffUser,
    invoice_id: int | None = None,
    method: PaymentMethod | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
):
    stmt = (
        select(Payment)
        .where(*_conditions(invoice_id, method, from_date, to_date))
        .options(*_LOAD)
        .order_by(Payment.payment_date.desc(), Payment.id.desc())
    )
    rows = (
        (
            p.payment_date,
            p.invoice.number or f"Draft #{p.invoice_id}",
            p.invoice.customer.name,
            p.method,
            p.amount,
            p.note,
            p.recorded_by.name if p.recorded_by else None,
        )
        for p in db.scalars(stmt)
    )
    header = ["Date", "Invoice", "Customer", "Method", "Amount", "Note", "Recorded by"]
    return csv_response("payments", header, rows)


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(body: PaymentIn, db: Db, user: StaffUser):
    payment = record_payment(db, body, user)
    db.commit()
    return payment_out(db.scalar(select(Payment).where(Payment.id == payment.id).options(*_LOAD)))
