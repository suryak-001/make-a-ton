"""The invoice as a PDF in the company's name: who can download it, what it says, and that the email carries it."""

from datetime import date

import pytest

from app.models import CompanyProfile, Customer
from app.services.company import MOCK_COMPANY
from tests.test_money_api import confirmed_invoice, pay

TODAY = date.today()


def text_of(response) -> str:
    """The PDF's page content is stored uncompressed, so the words the reader sees are in the bytes."""
    return response.content.decode("latin-1")


def test_staff_download_an_invoice_pdf_in_the_company_name(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog, number="PDF-1")
    catalog.customer.address = "Plot 21, MG Road\nKochi"
    db.commit()
    login("staff@t.test")
    response = client.get(f"/api/invoices/{invoice.id}/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == f'attachment; filename="{invoice.number}.pdf"'
    assert response.content.startswith(b"%PDF")
    body = text_of(response)
    for expected in (
        MOCK_COMPANY["name"],
        "TAX INVOICE",
        invoice.number,
        catalog.customer.name,
        "Plot 21, MG Road",
        "Balance due",
    ):
        assert expected in body


def test_a_saved_company_profile_replaces_the_sample_one(client, users, catalog, login, db):
    db.add(CompanyProfile(**{**MOCK_COMPANY, "name": "Zenith Cloud LLP", "account_name": "Zenith Cloud LLP"}))
    invoice = confirmed_invoice(db, catalog, number="PDF-2")
    login("admin@t.test")
    body = text_of(client.get(f"/api/invoices/{invoice.id}/pdf"))
    assert "Zenith Cloud LLP" in body and MOCK_COMPANY["name"] not in body


def test_the_pdf_shows_payments_and_a_paid_stamp(client, users, catalog, login, db):
    invoice = confirmed_invoice(db, catalog, number="PDF-3")
    login("staff@t.test")
    assert pay(client, invoice, invoice.total).status_code == 201
    body = text_of(client.get(f"/api/invoices/{invoice.id}/pdf"))
    assert "PAYMENTS RECEIVED" in body and "PAID" in body


def test_a_customer_downloads_only_their_own_invoice(client, users, catalog, login, db):
    mine = confirmed_invoice(db, catalog, number="MINE")
    stranger = Customer(name="Other Co", email="other@t.test")
    db.add(stranger)
    db.flush()
    theirs = confirmed_invoice(db, catalog, number="THEIRS")
    theirs.customer_id = stranger.id
    db.commit()
    login("cust@t.test")
    ok = client.get(f"/api/portal-invoices/{mine.id}/pdf")
    assert ok.status_code == 200 and ok.content.startswith(b"%PDF")
    assert client.get(f"/api/portal-invoices/{theirs.id}/pdf").status_code == 404
    assert client.get(f"/api/invoices/{mine.id}/pdf").status_code == 403


def test_a_draft_is_not_available_to_the_customer(client, users, catalog, login, db):
    from app.enums import InvoiceStatus

    invoice = confirmed_invoice(db, catalog, number="DRAFTY")
    invoice.status = InvoiceStatus.DRAFT
    db.commit()
    login("cust@t.test")
    assert client.get(f"/api/portal-invoices/{invoice.id}/pdf").status_code == 404


def test_signed_out_visitors_get_nothing(client, users, catalog, db):
    invoice = confirmed_invoice(db, catalog, number="PDF-4")
    assert client.get(f"/api/invoices/{invoice.id}/pdf").status_code == 401
    assert client.get(f"/api/portal-invoices/{invoice.id}/pdf").status_code == 401


def test_sending_an_invoice_attaches_the_pdf(client, users, catalog, login, db, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.services.invoices.send_mail", lambda *args, **kwargs: sent.append((args, kwargs))
    )
    invoice = confirmed_invoice(db, catalog, number="PDF-5")
    login("staff@t.test")
    assert client.post(f"/api/invoices/{invoice.id}/send").status_code == 200
    ((args, kwargs),) = sent
    assert args[0] == catalog.customer.email and MOCK_COMPANY["name"] in args[1]
    [(name, data, mime)] = kwargs["attachments"]
    assert name == f"{invoice.number}.pdf" and mime == "application/pdf" and data.startswith(b"%PDF")


@pytest.mark.parametrize("lines", [1, 40])
def test_a_long_invoice_runs_onto_more_pages(db, catalog, lines):
    from decimal import Decimal

    from app.models import InvoiceLine
    from app.services.company import get_company
    from app.services.invoice_pdf import render_invoice_pdf

    invoice = confirmed_invoice(db, catalog, number=f"LONG-{lines}")
    for n in range(lines - 1):
        invoice.lines.append(
            InvoiceLine(
                description=f"Extra seat {n}", quantity=1, unit_price=Decimal("10"), total=Decimal("11.80")
            )
        )
    pdf = render_invoice_pdf(invoice, get_company(db))
    assert pdf.startswith(b"%PDF") and (b"/Count 2" in pdf) == (lines > 30)


@pytest.mark.parametrize(
    ("paid", "says", "never"),
    [
        ("0", "It is due on", "paid in full"),
        ("100", "remaining INR", "paid in full"),
        ("all", "paid in full", "due on"),
    ],
)
def test_the_invoice_email_matches_what_is_still_owed(
    client, users, catalog, login, db, monkeypatch, paid, says, never
):
    from tests.test_money_api import pay

    sent = []
    monkeypatch.setattr("app.services.invoices.send_mail", lambda *args, **kwargs: sent.append(args))
    invoice = confirmed_invoice(db, catalog, number="PDF-6")
    login("staff@t.test")
    if paid != "0":
        assert pay(client, invoice, invoice.total if paid == "all" else paid).status_code == 201
    assert client.post(f"/api/invoices/{invoice.id}/send").status_code == 200
    ((_, _, body),) = sent
    assert says in body and never not in body
