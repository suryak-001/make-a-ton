"""Billing runs, invoice browsing and guarded invoice actions."""

from datetime import date
from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from app.core.csv_export import csv_response
from app.core.deps import AdminUser, Db, StaffUser
from app.core.pagination import Page, Pages, like_pattern, paginate
from app.enums import InvoiceStatus
from app.models import Customer, Invoice
from app.schemas.money import BillingRunIn, BillingRunOut, InvoiceOut
from app.services import invoices as svc
from app.services.billing import rebill_invoice, run_billing
from app.services.company import get_company
from app.services.invoice_pdf import invoice_filename, render_invoice_pdf
from app.services.invoice_queries import overdue_conditions, present_conditions
from app.services.money_views import INVOICE_LOAD, invoice_out, load_invoice

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def _conditions(
    status: InvoiceStatus | None,
    customer_id: int | None,
    from_date: date | None,
    to_date: date | None,
    overdue: bool | None,
    q: str | None,
) -> list:
    conditions = present_conditions(
        (status, lambda v: Invoice.status == v),
        (customer_id, lambda v: Invoice.customer_id == v),
        (from_date, lambda v: Invoice.invoice_date >= v),
        (to_date, lambda v: Invoice.invoice_date <= v),
    )
    if overdue:
        conditions += overdue_conditions()
    if q and q.strip():
        like = like_pattern(q)
        customers = select(Customer.id).where(Customer.name.ilike(like, escape="\\"))
        conditions.append(or_(Invoice.number.ilike(like, escape="\\"), Invoice.customer_id.in_(customers)))
    return conditions


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
    q: str | None = None,
):
    """`q` matches the invoice number or the customer's name."""
    conditions = _conditions(status, customer_id, from_date, to_date, overdue, q)
    stmt = select(Invoice).where(*conditions).options(*INVOICE_LOAD).order_by(Invoice.id.desc())
    rows, total = paginate(db, stmt, pages)
    return Page(items=[invoice_out(i) for i in rows], total=total, page=pages.page, page_size=pages.page_size)


@router.get("/export.csv")
def export_invoices(
    db: Db,
    _: StaffUser,
    status: InvoiceStatus | None = None,
    customer_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    overdue: bool | None = None,
    q: str | None = None,
):
    """Every invoice the list's filters match, without paging."""
    conditions = _conditions(status, customer_id, from_date, to_date, overdue, q)
    stmt = (
        select(Invoice)
        .where(*conditions)
        .options(joinedload(Invoice.customer), joinedload(Invoice.subscription))
        .order_by(Invoice.id.desc())
    )
    today = date.today()
    rows = (
        (
            i.number or f"Draft #{i.id}",
            i.status,
            i.customer.name,
            i.customer.email,
            i.subscription.number,
            i.period_start,
            i.period_end,
            i.invoice_date,
            i.due_date,
            i.subtotal,
            i.discount_total,
            i.tax_total,
            i.total,
            i.amount_paid,
            i.total - i.amount_paid if i.status == InvoiceStatus.CONFIRMED else "0.00",
            "yes"
            if i.status == InvoiceStatus.CONFIRMED and i.due_date < today and i.amount_paid < i.total
            else "no",
        )
        for i in db.scalars(stmt)
    )
    header = [
        "Invoice",
        "Status",
        "Customer",
        "Email",
        "Subscription",
        "Period start",
        "Period end",
        "Invoice date",
        "Due date",
        "Subtotal",
        "Discount",
        "Tax",
        "Total",
        "Paid",
        "Outstanding",
        "Overdue",
    ]
    return csv_response("invoices", header, rows)


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


def pdf_response(db, invoice) -> Response:
    """The invoice as a downloadable PDF in the company's name. Shared with the customer portal, which passes only
    an invoice it has already checked belongs to the signed-in customer."""
    data = render_invoice_pdf(invoice, get_company(db))
    return Response(
        data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice_filename(invoice)}"'},
    )


@router.get("/{invoice_id}/pdf")
def download_pdf(invoice_id: int, db: Db, _: StaffUser):
    return pdf_response(db, svc.get_invoice(db, invoice_id))
