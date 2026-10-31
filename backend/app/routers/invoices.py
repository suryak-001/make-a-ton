"""Billing runs, invoice browsing and guarded invoice actions."""

from datetime import date
from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.core.deps import AdminUser, Db, StaffUser
from app.core.pagination import Page, Pages, paginate
from app.enums import InvoiceStatus
from app.models import Invoice
from app.schemas.money import BillingRunIn, BillingRunOut, InvoiceOut
from app.services import invoices as svc
from app.services.billing import rebill_invoice, run_billing
from app.services.invoice_queries import overdue_conditions, present_conditions
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
    conditions = present_conditions(
        (status, lambda v: Invoice.status == v),
        (customer_id, lambda v: Invoice.customer_id == v),
        (from_date, lambda v: Invoice.invoice_date >= v),
        (to_date, lambda v: Invoice.invoice_date <= v),
    )
    if overdue:
        conditions += overdue_conditions()
    stmt = select(Invoice).where(*conditions).options(*INVOICE_LOAD).order_by(Invoice.id.desc())
    rows, total = paginate(db, stmt, pages)
    return Page(items=[invoice_out(i) for i in rows], total=total, page=pages.page, page_size=pages.page_size)


@router.post("/run-billing", response_model=BillingRunOut)
def billing_run(body: BillingRunIn, db: Db, _: StaffUser):
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


@router.post("/{invoice_id}/rebill", response_model=InvoiceOut, status_code=201)
def rebill(invoice_id: int, db: Db, _: AdminUser):
    """Bills a cancelled invoice's period again as a new Draft. Admin only; the billing run never does it."""
    invoice = rebill_invoice(db, invoice_id)
    db.commit()
    return invoice_out(load_invoice(db, invoice.id))


@router.post("/{invoice_id}/send", response_model=InvoiceOut)
def send(invoice_id: int, db: Db, _: StaffUser):
    svc.send_invoice(db, invoice_id)
    db.commit()
    return invoice_out(load_invoice(db, invoice_id))


def _print_row(line) -> str:
    cells = (line.description, line.quantity, line.unit_price, line.tax_amount, line.total)
    return "<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in cells) + "</tr>"


def _print_html(invoice: InvoiceOut) -> str:
    """A print-friendly page. Everything that came from the database is escaped."""
    number = escape(invoice.number or "Draft")
    rows = "".join(_print_row(line) for line in invoice.lines)
    return f"""<!doctype html><html><head><title>{number}</title><style>
    body{{font:14px system-ui;max-width:900px;margin:40px auto;color:#18202f}} table{{width:100%;border-collapse:collapse;margin-top:32px}}
    th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left}} .totals{{margin-left:auto;width:300px;margin-top:24px}}
    @media print{{button{{display:none}} body{{margin:0}}}}</style></head><body><button onclick="print()">Print / Save PDF</button>
    <h1>Invoice {number}</h1><p>{escape(invoice.customer.name)} · {invoice.period_start} to {invoice.period_end}</p>
    <table><thead><tr><th>Description</th><th>Qty</th><th>Price</th><th>Tax</th><th>Total</th></tr></thead><tbody>{rows}</tbody></table>
    <div class="totals"><p>Subtotal: {invoice.subtotal}</p><p>Discount: {invoice.discount_total}</p><p>Tax: {invoice.tax_total}</p><h2>Total: {invoice.total}</h2></div></body></html>"""


@router.get("/{invoice_id}/print", response_class=HTMLResponse)
def print_invoice(invoice_id: int, db: Db, _: StaffUser):
    return HTMLResponse(_print_html(invoice_out(load_invoice(db, invoice_id))))
