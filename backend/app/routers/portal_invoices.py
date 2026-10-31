"""A customer's own invoices. Every lookup is ownership-scoped."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.core.deps import CustomerUser, Db
from app.core.errors import NotFound
from app.core.pagination import Page, Pages, paginate
from app.enums import InvoiceStatus
from app.models import Invoice
from app.routers.invoices import _print_html
from app.schemas.money import InvoiceOut
from app.services.money_views import INVOICE_LOAD, invoice_out

router = APIRouter(prefix="/api/portal-invoices", tags=["portal-invoices"])


def _customer_id(user) -> int:
    if user.customer is None:
        raise NotFound("Invoice not found")
    return user.customer.id


@router.get("", response_model=Page[InvoiceOut])
def list_mine(db: Db, user: CustomerUser, pages: Pages):
    if user.customer is None:
        return Page(items=[], total=0, page=pages.page, page_size=pages.page_size)
    stmt = (
        select(Invoice)
        .where(Invoice.customer_id == user.customer.id, Invoice.status != InvoiceStatus.DRAFT)
        .options(*INVOICE_LOAD)
        .order_by(Invoice.id.desc())
    )
    rows, total = paginate(db, stmt, pages)
    return Page(items=[invoice_out(i) for i in rows], total=total, page=pages.page, page_size=pages.page_size)


def _mine(invoice_id: int, db: Db, user) -> Invoice:
    invoice = db.scalar(
        select(Invoice)
        .where(
            Invoice.id == invoice_id,
            Invoice.customer_id == _customer_id(user),
            Invoice.status != InvoiceStatus.DRAFT,
        )
        .options(*INVOICE_LOAD)
    )
    if invoice is None:
        raise NotFound("Invoice not found")
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_mine(invoice_id: int, db: Db, user: CustomerUser):
    return invoice_out(_mine(invoice_id, db, user))


@router.get("/{invoice_id}/print", response_class=HTMLResponse)
def print_mine(invoice_id: int, db: Db, user: CustomerUser):
    return HTMLResponse(_print_html(invoice_out(_mine(invoice_id, db, user))))
