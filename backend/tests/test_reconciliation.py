"""Bank reconciliation: reading statements, suggesting matches, and recording each statement line once."""

from datetime import timedelta
from decimal import Decimal

import pytest

from app.core.errors import Invalid
from app.enums import InvoiceStatus
from app.models import Customer, Invoice, Payment
from app.services.reconciliation import parse_statement
from tests.test_money_api import TODAY, confirmed_invoice

D = Decimal
DAY = f"{TODAY:%d/%m/%Y}"


def numbered(db, catalog, seq: int, *, customer=None, number="SUB-T-1") -> Invoice:
    """A confirmed invoice numbered the way the app numbers them (INV-<year>-<5 digits>)."""
    invoice = confirmed_invoice(db, catalog, number=number)
    invoice.number = f"INV-{TODAY.year}-{seq:05d}"
    if customer is not None:
        invoice.customer_id = customer.id
    db.commit()
    return invoice


def statement(*rows: tuple[str, str, str]) -> str:
    """rows of (narration, withdrawal, deposit), all dated today."""
    lines = ["Date,Narration,Withdrawal Amt.,Deposit Amt."]
    lines += [f'{DAY},"{narration}","{debit}","{credit}"' for narration, debit, credit in rows]
    return "\n".join(lines)


def preview(client, text):
    response = client.post("/api/reconciliation/preview", json={"csv": text})
    assert response.status_code == 200, response.text
    return response.json()


def approve(rows):
    return [
        {
            "ref": r["ref"],
            "invoice_id": r["invoice"]["id"],
            "amount": r["amount"],
            "payment_date": r["date"],
            "method": r["method"],
            "description": r["description"],
        }
        for r in rows
        if r["status"] == "matched"
    ]


# ───────────────────────────── reading ─────────────────────────────


def test_reads_bank_layouts_and_skips_debits():
    text = 'Account 1234\n\nTxn Date;Particulars;Debit;Credit\n05-01-2026;NEFT ACME;;"1,23,456.50"\n06-01-2026;ATM;500.00;\n\n'
    parsed = parse_statement(text)
    assert [(c.date.isoformat(), c.amount) for c in parsed.credits] == [("2026-01-05", D("123456.50"))]
    assert parsed.debits_skipped == 1 and parsed.problems == []

    signed = parse_statement(
        "Date,Description,Amount\n2026-01-05,IN,₹ 500\n2026-01-05,OUT,-20\n05 Jan 2026,IN,10.00 CR"
    )
    assert [c.amount for c in signed.credits] == [D("500.00"), D("10.00")]
    assert signed.debits_skipped == 1


def test_unreadable_rows_are_reported_with_their_line_number():
    parsed = parse_statement(
        "Date,Narration,Deposit\n31/02/2026,X,10\n01/03/2026,Y,abc\n,Z,5\n01/03/2026,OK,7"
    )
    assert [(p.line, p.error) for p in parsed.problems] == [
        (2, "Couldn't read the date '31/02/2026'."),
        (3, "Couldn't read the amount 'abc'."),
        (4, "This row has no date."),
    ]
    assert [c.description for c in parsed.credits] == ["OK"]


def test_a_file_without_the_columns_is_refused():
    with pytest.raises(Invalid, match="Narration"):
        parse_statement("Name,Value\nA,1")


def test_identical_lines_get_different_fingerprints():
    parsed = parse_statement(statement(("UPI ACME", "", "100"), ("UPI ACME", "", "100")))
    first, second = parsed.credits
    assert first.ref != second.ref and len(first.ref) == 64


# ───────────────────────────── matching ─────────────────────────────


def test_matches_by_invoice_number_even_when_mangled(client, users, catalog, login, db):
    invoice = numbered(db, catalog, 12)
    login("staff@t.test")
    rows = preview(client, statement((f"IMPS-77-INV{TODAY.year}00012", "", str(invoice.total))))["rows"]
    assert rows[0]["status"] == "matched" and rows[0]["confidence"] == "high"
    assert rows[0]["invoice"]["number"] == invoice.number


def test_a_part_payment_by_number_leaves_the_rest_for_the_next_line(client, users, catalog, login, db):
    invoice = numbered(db, catalog, 1)
    half = (invoice.total / 2).quantize(D("0.01"))
    login("staff@t.test")
    rows = preview(
        client,
        statement(
            (f"UPI {invoice.number}", "", str(half)),
            (f"UPI {invoice.number}", "", str(invoice.total - half)),
            (f"UPI {invoice.number}", "", "1.00"),
        ),
    )["rows"]
    assert [r["status"] for r in rows] == ["matched", "matched", "unmatched"]
    assert "Part payment" in rows[0]["reason"] and rows[1]["reason"] == "Invoice number and amount match."
    assert "already settled" in rows[2]["reason"]


def test_paying_more_than_the_balance_is_never_suggested(client, users, catalog, login, db):
    invoice = numbered(db, catalog, 1)
    login("staff@t.test")
    row = preview(client, statement((f"NEFT {invoice.number}", "", str(invoice.total + 1))))["rows"][0]
    assert row["status"] == "unmatched" and "more than" in row["reason"]


def test_a_paid_invoice_number_is_explained(client, users, catalog, login, db):
    invoice = numbered(db, catalog, 1)
    invoice.status = InvoiceStatus.PAID
    db.commit()
    login("staff@t.test")
    row = preview(client, statement((f"NEFT {invoice.number}", "", "10")))["rows"][0]
    assert row["status"] == "unmatched" and "which is paid" in row["reason"]


def test_matches_by_customer_name_and_amount(client, users, catalog, login, db):
    northwind = Customer(name="Northwind Traders Pvt Ltd", email="n@x.test")
    db.add(northwind)
    db.commit()
    numbered(db, catalog, 1)  # Cust Co, same amount: the name decides
    theirs = numbered(db, catalog, 2, customer=northwind, number="SUB-T-2")
    login("staff@t.test")
    rows = preview(
        client,
        statement(
            ("NEFT CR-ICIC0001-NORTHWIND TRADERS-SUBSCRIPTION", "", str(theirs.total)),
            ("NEFT CR-NORTHWIND TRADERS", "", "5.00"),
        ),
    )["rows"]
    assert rows[0]["confidence"] == "medium" and rows[0]["invoice"]["id"] == theirs.id
    assert rows[1]["status"] == "unmatched" and "Looks like Northwind" in rows[1]["reason"]


def test_amount_alone_matches_only_when_it_is_unique(client, users, catalog, login, db):
    invoice = numbered(db, catalog, 1)
    login("staff@t.test")
    row = preview(client, statement(("CASH DEPOSIT", "", str(invoice.total))))["rows"][0]
    assert row["confidence"] == "low" and row["method"] == "CASH"

    numbered(db, catalog, 2, number="SUB-T-2")  # same amount twice: too ambiguous to guess
    row = preview(client, statement(("CASH DEPOSIT", "", str(invoice.total))))["rows"][0]
    assert row["status"] == "unmatched" and "2 open invoices" in row["reason"]


# ───────────────────────────── recording ─────────────────────────────


def test_recording_pays_the_invoices_once_however_often_it_is_uploaded(client, users, catalog, login, db):
    invoice = numbered(db, catalog, 1)
    login("staff@t.test")
    text = statement((f"UPI/ACME/{invoice.number}", "", str(invoice.total)))
    items = approve(preview(client, text)["rows"])

    first = client.post("/api/reconciliation/apply", json={"items": items}).json()
    assert (first["recorded"], first["amount_recorded"]) == (1, str(invoice.total))
    db.refresh(invoice)
    assert invoice.status == InvoiceStatus.PAID
    payment = db.query(Payment).one()
    assert payment.method == "UPI" and payment.note.startswith("Bank statement: UPI/ACME/")
    assert payment.recorded_by_id == users["staff"].id

    again = client.post("/api/reconciliation/apply", json={"items": items}).json()
    assert (again["recorded"], again["already_recorded"]) == (0, 1)
    assert preview(client, text)["rows"][0]["status"] == "already_recorded"
    assert db.query(Payment).count() == 1


def test_recorded_lines_report_the_balance_left_on_their_invoice(client, users, catalog, login, db):
    invoice = numbered(db, catalog, 1)
    login("staff@t.test")
    base = {"invoice_id": invoice.id, "method": "UPI", "description": "x", "payment_date": str(TODAY)}
    items = [{**base, "ref": "a" * 64, "amount": "100.00"}, {**base, "ref": "b" * 64, "amount": "50.00"}]
    result = client.post("/api/reconciliation/apply", json={"items": items}).json()
    # Both lines show the balance after the whole run, not after their own line.
    assert [r["outstanding"] for r in result["results"]] == [str(invoice.total - Decimal("150.00"))] * 2


def test_one_failing_line_does_not_stop_the_others(client, users, catalog, login, db):
    good = numbered(db, catalog, 1)
    cancelled = numbered(db, catalog, 2, number="SUB-T-2")
    login("staff@t.test")
    items = approve(
        preview(
            client,
            statement(
                (f"NEFT {good.number}", "", str(good.total)), (f"NEFT {cancelled.number}", "", "10.00")
            ),
        )["rows"]
    )
    cancelled.status = InvoiceStatus.CANCELLED  # cancelled between preview and apply
    db.commit()
    result = client.post("/api/reconciliation/apply", json={"items": items}).json()
    assert (result["recorded"], result["failed"]) == (1, 1)
    assert result["results"][1]["message"] == "A cancelled invoice can't take payments."


def test_future_dates_and_overpayments_are_refused_line_by_line(client, users, catalog, login, db):
    invoice = numbered(db, catalog, 1)
    login("staff@t.test")
    base = {"invoice_id": invoice.id, "method": "UPI", "description": "x", "payment_date": str(TODAY)}
    items = [
        {**base, "ref": "a" * 64, "amount": str(invoice.total + 1)},
        {**base, "ref": "b" * 64, "amount": "1.00", "payment_date": str(TODAY + timedelta(days=1))},
    ]
    result = client.post("/api/reconciliation/apply", json={"items": items}).json()
    assert result["failed"] == 2
    assert "exceeds the outstanding" in result["results"][0]["message"]
    assert "future" in result["results"][1]["message"]


def test_the_sample_statement_shows_every_kind_of_match(client, users, catalog, login, db):
    for seq in range(1, 6):
        numbered(db, catalog, seq, number=f"SUB-T-{seq}")
    login("staff@t.test")
    sample = client.get("/api/reconciliation/sample.csv")
    assert sample.status_code == 200 and "attachment" in sample.headers["content-disposition"]
    result = preview(client, sample.text)
    assert result["debits_skipped"] == 2 and result["problems"] == []
    statuses = [r["status"] for r in result["rows"]]
    assert statuses.count("matched") >= 4 and statuses[-1] == "unmatched"


def test_reconciliation_is_for_staff_only(client, users, login):
    login("cust@t.test")
    assert client.post("/api/reconciliation/preview", json={"csv": "x"}).status_code == 403
    assert client.get("/api/reconciliation/sample.csv").status_code == 403
