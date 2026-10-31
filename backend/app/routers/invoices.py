"""Billing runs, invoice browsing and guarded invoice actions."""

from datetime import date

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.core.deps import AdminUser, Db, StaffUser
from app.core.pagination import Page, Pages, paginate
from app.enums import InvoiceStatus
from app.models import Invoice
from app.schemas.money import BillingRunIn, BillingRunOut, InvoiceOut
from app.services import invoices as svc
from app.services.billing import run_billing
from app.services.money_views import INVOICE_LOAD, invoice_out, load_invoice

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("", response_model=Page[InvoiceOut])
def list_invoices(
    db: Db,
    _: StaffUser,
    pages: Pages,
    status: InvoiceStatus | None = None,
    customer_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    overdue: bool | None = None,
):
    stmt = select(Invoice).options(*INVOICE_LOAD).order_by(Invoice.id.desc())
    if status:
        stmt = stmt.where(Invoice.status == status)
    if customer_id:
        stmt = stmt.where(Invoice.customer_id == customer_id)
    if from_date:
        stmt = stmt.where(Invoice.invoice_date >= from_date)
    if to_date:
        stmt = stmt.where(Invoice.invoice_date <= to_date)
    if overdue:
        stmt = stmt.where(
            Invoice.status == InvoiceStatus.CONFIRMED,
            Invoice.due_date < date.today(),
            Invoice.amount_paid < Invoice.total,
        )
    rows, total = paginate(db, stmt, pages)
    return Page(items=[invoice_out(i) for i in rows], total=total, page=pages.page, page_size=pages.page_size)


@router.post("/run-billing", response_model=BillingRunOut)
def billing_run(body: BillingRunIn, db: Db, _: AdminUser):
    result = run_billing(db, body.as_of or date.today())
    db.commit()
    return result


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Db, _: StaffUser):
    return invoice_out(load_invoice(db, invoice_id))


@router.post("/{invoice_id}/confirm", response_model=InvoiceOut)
def confirm(invoice_id: int, db: Db, _: StaffUser):
    svc.confirm_invoice(db, invoice_id)
    db.commit()
    return invoice_out(load_invoice(db, invoice_id))


@router.post("/{invoice_id}/cancel", response_model=InvoiceOut)
def cancel(invoice_id: int, db: Db, _: StaffUser):
    svc.cancel_invoice(db, invoice_id)
    db.commit()
    return invoice_out(load_invoice(db, invoice_id))


@router.post("/{invoice_id}/send", response_model=InvoiceOut)
def send(invoice_id: int, db: Db, _: StaffUser):
    svc.send_invoice(db, invoice_id)
    db.commit()
    return invoice_out(load_invoice(db, invoice_id))


def _print_html(invoice: InvoiceOut) -> str:
    rows = "".join(
        f"<tr><td>{line.description}</td><td>{line.quantity}</td><td>{line.unit_price}</td><td>{line.tax_amount}</td><td>{line.total}</td></tr>"
        for line in invoice.lines
    )
    return f"""<!doctype html><html><head><title>{invoice.number or "Draft invoice"}</title><style>
    body{{font:14px system-ui;max-width:900px;margin:40px auto;color:#18202f}} table{{width:100%;border-collapse:collapse;margin-top:32px}}
    th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left}} .totals{{margin-left:auto;width:300px;margin-top:24px}}
    @media print{{button{{display:none}} body{{margin:0}}}}</style></head><body><button onclick="print()">Print / Save PDF</button>
    <h1>Invoice {invoice.number or "Draft"}</h1><p>{invoice.customer.name} · {invoice.period_start} to {invoice.period_end}</p>
    <table><thead><tr><th>Description</th><th>Qty</th><th>Price</th><th>Tax</th><th>Total</th></tr></thead><tbody>{rows}</tbody></table>
    <div class="totals"><p>Subtotal: {invoice.subtotal}</p><p>Discount: {invoice.discount_total}</p><p>Tax: {invoice.tax_total}</p><h2>Total: {invoice.total}</h2></div></body></html>"""


@router.get("/{invoice_id}/print", response_class=HTMLResponse)
def print_invoice(invoice_id: int, db: Db, _: StaffUser):
    return HTMLResponse(_print_html(invoice_out(load_invoice(db, invoice_id))))
