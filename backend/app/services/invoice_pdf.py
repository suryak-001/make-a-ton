"""Draws an invoice as a PDF in the issuing company's name. Pure rendering: it reads the invoice and the company and
returns bytes, so the staff download, the customer download and the email attachment are the same file."""

from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.enums import InvoiceStatus
from app.models import CompanyProfile, Invoice

BRAND = colors.HexColor("#1849d6")
INK = colors.HexColor("#18202f")
MUTED = colors.HexColor("#6b7280")
LINE = colors.HexColor("#d9dce3")
SURFACE = colors.HexColor("#f4f5f8")

# Helvetica has no rupee sign, so amounts carry the currency code instead.
CURRENCY = "INR"

STAMPS = {
    InvoiceStatus.PAID: ("PAID", colors.HexColor("#1f9d55")),
    InvoiceStatus.DRAFT: ("DRAFT", colors.HexColor("#9ca3af")),
    InvoiceStatus.CANCELLED: ("CANCELLED", colors.HexColor("#d64545")),
}


def invoice_filename(invoice: Invoice) -> str:
    return f"{invoice.number or f'draft-{invoice.id}'}.pdf"


def _style(name: str, **over) -> ParagraphStyle:
    base = {"fontName": "Helvetica", "fontSize": 9, "leading": 12, "textColor": INK}
    return ParagraphStyle(name, **{**base, **over})


BODY = _style("body")
SMALL = _style("small", fontSize=8, leading=11, textColor=MUTED)
BOLD = _style("bold", fontName="Helvetica-Bold")
RIGHT = _style("right", alignment=TA_RIGHT)
RIGHT_BOLD = _style("rightBold", alignment=TA_RIGHT, fontName="Helvetica-Bold")
TITLE = _style("title", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=BRAND)
DOC_TITLE = _style("doc", fontName="Helvetica-Bold", fontSize=15, leading=18, alignment=TA_RIGHT)
HEAD = _style("head", fontName="Helvetica-Bold", fontSize=8, textColor=MUTED)
HEAD_RIGHT = _style("headRight", fontName="Helvetica-Bold", fontSize=8, textColor=MUTED, alignment=TA_RIGHT)


def _p(text: object, style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def amount(value: Decimal) -> str:
    return f"{CURRENCY} {value:,.2f}"


def _date(value) -> str:
    return value.strftime("%d %b %Y")


def _header(invoice: Invoice, company: CompanyProfile) -> Table:
    left = [_p(company.name, TITLE)]
    if company.tagline:
        left.append(_p(company.tagline, SMALL))
    left.append(Spacer(1, 3 * mm))
    left.append(_p(company.address, BODY))
    contact = " · ".join(part for part in (company.email, company.phone, company.website) if part)
    left.append(_p(contact, SMALL))
    ids = " · ".join(
        part
        for part in (
            f"GSTIN {company.gstin}" if company.gstin else "",
            f"PAN {company.pan}" if company.pan else "",
        )
        if part
    )
    if ids:
        left.append(_p(ids, SMALL))
    right = [
        _p("TAX INVOICE" if invoice.status != InvoiceStatus.DRAFT else "DRAFT INVOICE", DOC_TITLE),
        Spacer(1, 2 * mm),
        _p(invoice.number or f"Draft #{invoice.id}", RIGHT_BOLD),
    ]
    table = Table([[left, right]], colWidths=[110 * mm, 70 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def _parties(invoice: Invoice) -> Table:
    customer = invoice.customer
    bill_to = [_p("BILL TO", HEAD), Spacer(1, 1 * mm), _p(customer.name, BOLD)]
    if customer.address:
        bill_to.append(_p(customer.address, BODY))
    bill_to.append(_p(customer.email, SMALL))
    if customer.phone:
        bill_to.append(_p(customer.phone, SMALL))
    facts = [
        ("Invoice date", _date(invoice.invoice_date)),
        ("Due date", _date(invoice.due_date)),
        ("Billing period", f"{_date(invoice.period_start)} to {_date(invoice.period_end)}"),
        ("Subscription", invoice.subscription.number),
    ]
    meta = Table([[_p(k, SMALL), _p(v, RIGHT)] for k, v in facts], colWidths=[28 * mm, 52 * mm])
    meta.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    table = Table([[bill_to, meta]], colWidths=[100 * mm, 80 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LINEABOVE", (0, 0), (-1, 0), 0.6, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        )
    )
    return table


def _lines(invoice: Invoice) -> Table:
    rows = [
        [
            _p(h, HEAD if i == 0 else HEAD_RIGHT)
            for i, h in enumerate(("DESCRIPTION", "QTY", "UNIT PRICE", "DISCOUNT", "TAX", "TOTAL"))
        ]
    ]
    for line in invoice.lines:
        tax = f"{amount(line.tax_amount)}" + (
            f"<br/><font size=7 color='#6b7280'>{line.tax_rate:g}%</font>" if line.tax_rate else ""
        )
        rows.append(
            [
                _p(line.description),
                _p(line.quantity, RIGHT),
                _p(amount(line.unit_price), RIGHT),
                _p(amount(line.discount_amount) if line.discount_amount else "-", RIGHT),
                Paragraph(tax, RIGHT),
                _p(amount(line.total), RIGHT_BOLD),
            ]
        )
    table = Table(rows, colWidths=[56 * mm, 12 * mm, 29 * mm, 25 * mm, 25 * mm, 33 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), SURFACE),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
                ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _totals(invoice: Invoice) -> Table:
    owed = max(invoice.total - invoice.amount_paid, Decimal("0"))
    rows = [("Subtotal", amount(invoice.subtotal))]
    if invoice.discount_total:
        rows.append(("Discount", f"- {amount(invoice.discount_total)}"))
    rows += [("Tax", amount(invoice.tax_total)), ("Total", amount(invoice.total))]
    if invoice.amount_paid:
        rows.append(("Paid", f"- {amount(invoice.amount_paid)}"))
    rows.append(("Balance due", amount(owed)))
    table = Table(
        [
            [
                _p(k, BOLD if k in ("Total", "Balance due") else BODY),
                _p(v, RIGHT_BOLD if k in ("Total", "Balance due") else RIGHT),
            ]
            for k, v in rows
        ],
        colWidths=[35 * mm, 45 * mm],
        hAlign="RIGHT",
    )
    last = len(rows) - 1
    table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, last), (-1, last), 0.8, INK),
                ("BACKGROUND", (0, last), (-1, last), SURFACE),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _payments(invoice: Invoice) -> list:
    payments = sorted(invoice.payments, key=lambda p: (p.payment_date, p.id))
    if not payments:
        return []
    rows = [[_p("PAYMENTS RECEIVED", HEAD), _p("METHOD", HEAD), _p("AMOUNT", HEAD_RIGHT)]]
    rows += [
        [_p(_date(p.payment_date)), _p(p.method.replace("_", " ").title()), _p(amount(p.amount), RIGHT)]
        for p in payments
    ]
    table = Table(rows, colWidths=[60 * mm, 60 * mm, 40 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return [Spacer(1, 6 * mm), table]


def _how_to_pay(company: CompanyProfile) -> list:
    details = [
        ("Bank", company.bank_name),
        ("Account name", company.account_name),
        ("Account number", company.account_number),
        ("IFSC", company.ifsc),
        ("UPI", company.upi_id),
    ]
    shown = [(k, v) for k, v in details if v]
    if not shown:
        return []
    table = Table([[_p(k, SMALL), _p(v)] for k, v in shown], colWidths=[30 * mm, 80 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return [Spacer(1, 8 * mm), _p("HOW TO PAY", HEAD), Spacer(1, 1 * mm), table]


def render_invoice_pdf(invoice: Invoice, company: CompanyProfile) -> bytes:
    """The invoice as a one-or-more page A4 PDF. Paid, draft and cancelled invoices carry a stamp across the page."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
        title=f"Invoice {invoice.number or invoice.id}",
        author=company.name,
        pageCompression=0,  # invoices are small; readable streams make the file easy to check
    )
    story = [
        _header(invoice, company),
        Spacer(1, 8 * mm),
        _parties(invoice),
        Spacer(1, 8 * mm),
        _lines(invoice),
        Spacer(1, 5 * mm),
        _totals(invoice),
        *_payments(invoice),
        *_how_to_pay(company),
    ]
    if company.terms:
        story += [Spacer(1, 8 * mm), _p(company.terms, SMALL)]
    stamp = STAMPS.get(invoice.status)

    def decorate(canvas, document) -> None:
        if stamp:
            text, colour = stamp
            canvas.saveState()
            canvas.setFillColor(colour)
            canvas.setFillAlpha(0.13)
            canvas.setFont("Helvetica-Bold", 90)
            canvas.translate(A4[0] / 2, A4[1] / 2)
            canvas.rotate(35)
            canvas.drawCentredString(0, 0, text)
            canvas.restoreState()
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(15 * mm, 10 * mm, f"{company.name} · {company.email}")
        canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return buffer.getvalue()
