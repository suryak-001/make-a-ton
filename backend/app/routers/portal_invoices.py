"""A customer's own invoices, and paying them online. Every lookup is ownership-scoped."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.core.deps import CustomerUser, Db
from app.core.errors import NotFound
from app.core.pagination import Page, Pages, paginate
from app.enums import InvoiceStatus
from app.models import Invoice
from app.routers.invoices import _print_html
from app.schemas.gateway import CheckoutOut, VerifyIn
from app.schemas.money import InvoiceOut
from app.services import gateway
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


@router.post("/{invoice_id}/checkout", response_model=CheckoutOut)
def start_checkout(invoice_id: int, db: Db, user: CustomerUser):
    """Opens an online payment for the invoice's balance. The amount is fixed here, not by the browser."""
    invoice = _mine(invoice_id, db, user)
    order = gateway.create_order(db, invoice)
    db.commit()
    return CheckoutOut(
        order_id=order.id,
        amount=order.amount,
        currency=gateway.CURRENCY,
        invoice_id=invoice.id,
        invoice_number=invoice.number,
        merchant=gateway.MERCHANT,
        customer_name=invoice.customer.name,
        customer_email=invoice.customer.email,
        test_mode=True,
    )


@router.post("/{invoice_id}/checkout/verify", response_model=InvoiceOut)
def verify_checkout(invoice_id: int, body: VerifyIn, db: Db, user: CustomerUser):
    """Checks the gateway's signature and records the payment (once, however often it is called)."""
    _mine(invoice_id, db, user)
    gateway.verify(db, user, invoice_id, body.order_id, body.payment_id, body.signature)
    db.commit()
    db.expire_all()
    return invoice_out(_mine(invoice_id, db, user))
