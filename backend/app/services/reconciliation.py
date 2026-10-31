"""Bank reconciliation: read a bank statement export, suggest which open invoice each credit pays, then record
the payments the team approves.

Matching, strongest first. Every suggestion says why it was made, and nothing is recorded until someone approves it.
  high    the narration names an open invoice (INV-2026-00012, INV202600012…) and the amount fits its balance
  medium  the narration names the customer and the amount equals one of their open balances
  low     only the amount matches, and exactly one open invoice has that balance
Statement lines are walked in file order and each match takes from the invoice's balance, so two lines can't both
settle the same amount.

Each statement line has a fingerprint (date, amount, narration and how many identical lines came before it in
the file). The payment it becomes stores that fingerprint under a unique constraint, so uploading the same
statement again shows those lines as already recorded and can never pay twice.
"""

import csv
import hashlib
import io
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DomainError, Invalid
from app.enums import InvoiceStatus, PaymentMethod
from app.models import Customer, Invoice, Payment, User
from app.schemas.money import PaymentIn
from app.schemas.reconciliation import (
    ApplyItemIn,
    ApplyOut,
    ApplyResultOut,
    InvoiceHint,
    PreviewOut,
    StatementProblem,
    StatementRowOut,
)
from app.services.payments import record_payment

MAX_ROWS = 2000
HEADER_SEARCH_ROWS = 15  # banks put a few lines of account details above the table
CENT = Decimal("0.01")

# ───────────────────────────── reading the statement ─────────────────────────────

# Column names as Indian and international banks export them (compared lower-cased, without "(…)" or dots).
HEADERS = {
    "date": {
        "date",
        "txn date",
        "transaction date",
        "value date",
        "posting date",
        "tran date",
        "value dt",
        "txn dt",
    },
    "description": {
        "description",
        "narration",
        "particulars",
        "details",
        "remarks",
        "transaction details",
        "transaction remarks",
        "memo",
    },
    "reference": {
        "ref no",
        "refno",
        "reference",
        "reference no",
        "ref",
        "chq/ref no",
        "chq/refno",
        "cheque no",
        "utr",
    },
    "credit": {"credit", "deposit", "deposits", "credit amount", "cr", "money in", "paid in", "deposit amt"},
    "debit": {
        "debit",
        "withdrawal",
        "withdrawals",
        "debit amount",
        "dr",
        "money out",
        "paid out",
        "withdrawal amt",
    },
    "amount": {"amount", "transaction amount", "amount inr"},
}
DATE_FORMATS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%Y-%m-%d",
    "%d/%m/%y",
    "%d-%m-%y",
    "%d %b %Y",
    "%d-%b-%Y",
    "%d-%b-%y",
    "%d %B %Y",
)


@dataclass
class StatementLine:
    line: int
    date: date
    description: str
    amount: Decimal
    ref: str = ""


@dataclass
class Statement:
    credits: list[StatementLine] = field(default_factory=list)
    debits_skipped: int = 0
    problems: list[StatementProblem] = field(default_factory=list)


def _header_key(cell: str) -> str:
    text = re.sub(r"\(.*?\)", "", cell).replace(".", "").strip().lower()
    return re.sub(r"\s+", " ", text)


def _find_columns(row: list[str]) -> dict[str, int] | None:
    columns: dict[str, int] = {}
    for index, cell in enumerate(row):
        key = _header_key(cell)
        for name, aliases in HEADERS.items():
            if key in aliases and name not in columns:
                columns[name] = index
    if "date" in columns and "description" in columns and ("credit" in columns or "amount" in columns):
        return columns
    return None


def _parse_date(text: str) -> date | None:
    text = text.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(text: str) -> Decimal | None:
    """'1,23,456.00', '₹ 500', '500.00 CR', '(120.00)' or '-120' -> Decimal (negative for debits). Blank -> None."""
    t = re.sub(r"(₹|INR|Rs\.?|,|\s)", "", text.strip(), flags=re.I)
    if not t:
        return None
    sign = Decimal(1)
    if t.upper().endswith("CR"):
        t = t[:-2]
    elif t.upper().endswith("DR"):
        t, sign = t[:-2], Decimal(-1)
    if t.startswith("(") and t.endswith(")"):
        t, sign = t[1:-1], Decimal(-1)
    try:
        return (Decimal(t) * sign).quantize(CENT)
    except InvalidOperation:
        raise ValueError(text) from None


def _cell(row: list[str], columns: dict[str, int], name: str) -> str:
    index = columns.get(name)
    return row[index].strip() if index is not None and index < len(row) else ""


def parse_statement(text: str) -> Statement:
    """Credits from a bank's CSV export. Debits are counted and left out; rows that can't be read are reported
    with their row number instead of failing the whole file."""
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿")), dialect))

    found = next(
        (
            (at, columns)
            for at, row in enumerate(rows[:HEADER_SEARCH_ROWS])
            if (columns := _find_columns(row))
        ),
        None,
    )
    if found is None:
        raise Invalid(
            "Couldn't find the date, narration and amount columns. The statement needs headers such as "
            "Date, Narration and Deposit (or Credit, or Amount).",
            field="csv",
        )

    header_at, columns = found
    statement = Statement()
    for offset, row in enumerate(rows[header_at + 1 :], start=header_at + 2):
        if not any(cell.strip() for cell in row):
            continue
        date_text = _cell(row, columns, "date")
        try:
            credit = _parse_amount(_cell(row, columns, "credit")) if "credit" in columns else None
            debit = _parse_amount(_cell(row, columns, "debit")) if "debit" in columns else None
            amount = _parse_amount(_cell(row, columns, "amount")) if "amount" in columns else None
        except ValueError as e:
            statement.problems.append(StatementProblem(line=offset, error=f"Couldn't read the amount '{e}'."))
            continue
        value = credit if credit is not None else amount
        if not date_text:
            if value is not None:  # an amount with no date: tell someone; a footer line with neither: skip it
                statement.problems.append(StatementProblem(line=offset, error="This row has no date."))
            continue
        when = _parse_date(date_text)
        if when is None:
            statement.problems.append(
                StatementProblem(line=offset, error=f"Couldn't read the date '{date_text}'.")
            )
            continue
        if value is None or value <= 0:
            if (debit is not None and debit != 0) or (value is not None and value < 0):
                statement.debits_skipped += 1
            continue
        description = " ".join(
            x for x in (_cell(row, columns, "description"), _cell(row, columns, "reference")) if x
        )
        statement.credits.append(StatementLine(line=offset, date=when, description=description, amount=value))
        if len(statement.credits) > MAX_ROWS:
            raise Invalid(f"A statement can have at most {MAX_ROWS} credits. Split the file.", field="csv")

    _fingerprint(statement.credits)
    return statement


def _fingerprint(lines: list[StatementLine]) -> None:
    seen: Counter[tuple] = Counter()
    for line in lines:
        key = (line.date.isoformat(), str(line.amount), " ".join(line.description.upper().split()))
        seen[key] += 1
        line.ref = hashlib.sha256("|".join((*key, str(seen[key]))).encode()).hexdigest()


# ───────────────────────────── matching ─────────────────────────────

INVOICE_REF = re.compile(r"INV[\s\-/_.]*(\d{4})[\s\-/_.]*(\d{1,6})(?!\d)", re.I)
GENERIC_WORDS = {
    "LTD",
    "LIMITED",
    "PVT",
    "PRIVATE",
    "INC",
    "LLC",
    "LLP",
    "CORP",
    "CORPORATION",
    "CO",
    "COMPANY",
    "THE",
    "AND",
    "OF",
}


@dataclass
class OpenInvoice:
    id: int
    number: str
    customer_id: int
    customer_name: str
    outstanding: Decimal
    due_date: date

    def hint(self, remaining: Decimal) -> InvoiceHint:
        return InvoiceHint(
            id=self.id,
            number=self.number,
            customer_name=self.customer_name,
            outstanding=remaining,
            due_date=self.due_date,
        )


def _rupees(amount: Decimal) -> str:
    """₹1,23,456.00: Indian digit grouping, as the screens show money."""
    whole, cents = f"{amount:.2f}".split(".")
    head, tail = whole[:-3], whole[-3:]
    groups = [head[max(i - 2, 0) : i] for i in range(len(head), 0, -2)][::-1]
    return "₹" + ",".join([*groups, tail] if head else [tail]) + "." + cents


def _invoice_key(text: str) -> tuple[int, int] | None:
    found = INVOICE_REF.search(text)
    return (int(found.group(1)), int(found.group(2))) if found else None


def _words(text: str) -> set[str]:
    return {w for w in re.split(r"[^A-Z0-9]+", text.upper()) if w}


def _name_words(name: str) -> frozenset[str]:
    """The words that identify a customer in a narration: 'Acme Retail Pvt Ltd' -> {ACME, RETAIL}."""
    return frozenset(w for w in _words(name) if w not in GENERIC_WORDS and (len(w) >= 3 or w.isdigit()))


def guess_method(description: str) -> PaymentMethod:
    words = _words(description)
    if "UPI" in words:
        return PaymentMethod.UPI
    if words & {"CHQ", "CHEQUE", "CLG", "CLEARING"}:
        return PaymentMethod.CHEQUE
    if words & {"CARD", "POS", "VISA", "MASTERCARD", "RUPAY"}:
        return PaymentMethod.CARD
    if "CASH" in words:
        return PaymentMethod.CASH
    return PaymentMethod.BANK_TRANSFER


class _Matcher:
    """Open invoices indexed three ways (by number, by customer name, by balance), with running balances."""

    def __init__(self, invoices: list[OpenInvoice], closed: dict[tuple[int, int], tuple[str, InvoiceStatus]]):
        self.closed = closed  # mentioned invoices that can't take money: (year, seq) -> (number, status)
        self.remaining = {i.id: i.outstanding for i in invoices}
        self.by_number: dict[tuple[int, int], OpenInvoice] = {}
        self.by_amount: defaultdict[Decimal, list[OpenInvoice]] = defaultdict(list)
        self.by_customer: defaultdict[int, list[OpenInvoice]] = defaultdict(list)
        self.names: dict[int, tuple[str, frozenset[str]]] = {}
        self.name_index: defaultdict[str, set[int]] = defaultdict(
            set
        )  # a word -> customers whose name has it
        for invoice in invoices:  # already ordered oldest due date first
            key = _invoice_key(invoice.number)
            if key:
                self.by_number[key] = invoice
            self.by_amount[invoice.outstanding].append(invoice)
            self.by_customer[invoice.customer_id].append(invoice)
            words = _name_words(invoice.customer_name)
            if words and invoice.customer_id not in self.names:
                self.names[invoice.customer_id] = (invoice.customer_name, words)
                for word in words:
                    self.name_index[word].add(invoice.customer_id)

    def take(self, invoice: OpenInvoice, amount: Decimal) -> InvoiceHint:
        hint = invoice.hint(self.remaining[invoice.id])
        self.remaining[invoice.id] -= amount
        return hint

    def match(self, line: StatementLine) -> tuple[str, str | None, str, InvoiceHint | None]:
        """(status, confidence, reason, invoice) for one credit."""
        key = _invoice_key(line.description)
        if key:
            return self._by_number(key, line.amount)
        customer = self._customer_named_in(line.description)
        if customer is not None:
            return self._by_customer(customer, line.amount)
        return self._by_amount(line.amount)

    def _by_number(self, key: tuple[int, int], amount: Decimal):
        invoice = self.by_number.get(key)
        if invoice is None:
            if key in self.closed:
                number, status = self.closed[key]
                return (
                    "unmatched",
                    None,
                    f"Mentions {number}, which is {status.lower()}. Pick the invoice by hand.",
                    None,
                )
            return (
                "unmatched",
                None,
                f"Mentions INV-{key[0]}-{key[1]:05d}, which isn't an open invoice.",
                None,
            )
        left = self.remaining[invoice.id]
        if left <= 0:
            return (
                "unmatched",
                None,
                f"{invoice.number} is already settled by an earlier line in this statement.",
                None,
            )
        if amount > left:
            return (
                "unmatched",
                None,
                f"Mentions {invoice.number} but pays more than its {_rupees(left)} outstanding.",
                None,
            )
        reason = (
            "Invoice number and amount match."
            if amount == left
            else f"Invoice number matches. Part payment: {_rupees(left - amount)} will still be owed."
        )
        return "matched", "high", reason, self.take(invoice, amount)

    def _customer_named_in(self, description: str) -> int | None:
        words = _words(description)
        candidates = {c for w in words for c in self.name_index.get(w, ())}
        named = [c for c in candidates if self.names[c][1] <= words]
        # The most specific name wins: "Acme Retail South" over "Acme Retail" when both appear.
        return max(named, key=lambda c: len(self.names[c][1]), default=None)

    def _by_customer(self, customer_id: int, amount: Decimal):
        name = self.names[customer_id][0]
        fits = [i for i in self.by_customer[customer_id] if self.remaining[i.id] == amount]
        if not fits:
            return (
                "unmatched",
                None,
                f"Looks like {name}, but none of their open invoices is for this amount.",
                None,
            )
        reason = "Customer name and amount match."
        if len(fits) > 1:
            reason = f"Customer name and amount match. Oldest of {len(fits)} invoices for this amount."
        return "matched", "medium", reason, self.take(fits[0], amount)

    def _by_amount(self, amount: Decimal):
        fits = [i for i in self.by_amount.get(amount, []) if self.remaining[i.id] == amount]
        if len(fits) == 1:
            return (
                "matched",
                "low",
                "Only the amount matches. Check it before recording.",
                self.take(fits[0], amount),
            )
        if fits:
            return (
                "unmatched",
                None,
                f"{len(fits)} open invoices are for this amount. Pick one by hand.",
                None,
            )
        return "unmatched", None, "No open invoice matches. Pick one by hand or leave it out.", None


def _open_invoices(db: Session) -> list[OpenInvoice]:
    stmt = (
        select(
            Invoice.id,
            Invoice.number,
            Invoice.customer_id,
            Customer.name,
            Invoice.total - Invoice.amount_paid,
            Invoice.due_date,
        )
        .join(Customer, Customer.id == Invoice.customer_id)
        .where(Invoice.status == InvoiceStatus.CONFIRMED, Invoice.amount_paid < Invoice.total)
        .order_by(Invoice.due_date, Invoice.id)
    )
    return [OpenInvoice(*row) for row in db.execute(stmt)]


def _closed_mentions(
    db: Session, lines: list[StatementLine]
) -> dict[tuple[int, int], tuple[str, InvoiceStatus]]:
    mentioned = {key for line in lines if (key := _invoice_key(line.description))}
    if not mentioned:
        return {}
    numbers = [f"INV-{year}-{seq:05d}" for year, seq in mentioned]
    rows = db.execute(
        select(Invoice.number, Invoice.status).where(
            Invoice.number.in_(numbers), Invoice.status != InvoiceStatus.CONFIRMED
        )
    )
    return {_invoice_key(number): (number, status) for number, status in rows}


def _already_recorded(db: Session, lines: list[StatementLine]) -> dict[str, str]:
    """Fingerprint -> invoice number, for statement lines that became payments before."""
    if not lines:
        return {}
    rows = db.execute(
        select(Payment.bank_ref, Invoice.number)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .where(Payment.bank_ref.in_([line.ref for line in lines]))
    )
    return dict(rows.all())


def preview(db: Session, text: str) -> PreviewOut:
    """What each credit on the statement would pay. Reads only; nothing is recorded."""
    statement = parse_statement(text)
    lines = statement.credits
    recorded = _already_recorded(db, lines)
    matcher = _Matcher(_open_invoices(db), _closed_mentions(db, lines))

    rows = []
    for line in lines:
        if line.ref in recorded:
            status, confidence, invoice = "already_recorded", None, None
            reason = f"Recorded earlier against {recorded[line.ref]}."
        else:
            status, confidence, reason, invoice = matcher.match(line)
        rows.append(
            StatementRowOut(
                ref=line.ref,
                line=line.line,
                date=line.date,
                description=line.description,
                amount=line.amount,
                method=guess_method(line.description),
                status=status,
                confidence=confidence,
                reason=reason,
                invoice=invoice,
            )
        )
    return PreviewOut(rows=rows, debits_skipped=statement.debits_skipped, problems=statement.problems)


# ───────────────────────────── recording ─────────────────────────────


def apply(db: Session, items: list[ApplyItemIn], user: User) -> ApplyOut:
    """Records each approved line as a payment, each in its own savepoint: one that fails (overpaid, invoice
    cancelled meanwhile) is reported and the rest still go through. The caller commits."""
    results: list[ApplyResultOut] = []
    recorded_amount = Decimal("0.00")
    for item in items:
        number = db.scalar(select(Invoice.number).where(Invoice.id == item.invoice_id))
        earlier = db.scalar(
            select(Invoice.number)
            .join(Payment, Payment.invoice_id == Invoice.id)
            .where(Payment.bank_ref == item.ref)
        )
        if earlier is not None:
            results.append(_result(item, "already_recorded", f"Recorded earlier against {earlier}.", earlier))
            continue
        try:
            body = PaymentIn(
                invoice_id=item.invoice_id,
                method=item.method,
                amount=item.amount,
                payment_date=item.payment_date,
                note=f"Bank statement: {item.description}"[:500],
            )
            with db.begin_nested():
                record_payment(db, body, user, bank_ref=item.ref)
        except DomainError as e:
            results.append(_result(item, "failed", e.message, number))
            continue
        except ValidationError as e:
            message = e.errors()[0]["msg"].removeprefix("Value error, ")
            results.append(_result(item, "failed", message, number))
            continue
        except IntegrityError:  # recorded by someone else between the check and the insert
            results.append(_result(item, "already_recorded", "Recorded by someone else just now.", number))
            continue
        recorded_amount += item.amount
        results.append(_result(item, "recorded", f"Recorded against {number}.", number))
    count = Counter(r.status for r in results)
    return ApplyOut(
        recorded=count["recorded"],
        already_recorded=count["already_recorded"],
        failed=count["failed"],
        amount_recorded=recorded_amount,
        results=results,
    )


def _result(item: ApplyItemIn, status: str, message: str, number: str | None) -> ApplyResultOut:
    return ApplyResultOut(ref=item.ref, status=status, message=message, invoice_number=number)


# ───────────────────────────── a sample to try it with ─────────────────────────────


def sample_statement(db: Session, today: date | None = None) -> str:
    """A bank statement export built from today's open invoices, laid out like an Indian bank's CSV (account
    details on top, Dr and Cr columns, DD/MM/YYYY dates). It shows every kind of match: invoice number and
    amount, a part payment, a mangled invoice number, a customer name with no number, a payment nobody can
    place, and debits that are skipped."""
    today = today or date.today()
    numbered = [i for i in _open_invoices(db) if _invoice_key(i.number)]
    # One invoice per customer reads most like a real statement; fill up with the rest when there are few customers.
    picked: list[OpenInvoice] = []
    for invoice in numbered:
        if len(picked) < 5 and invoice.customer_id not in {p.customer_id for p in picked}:
            picked.append(invoice)
    picked += [i for i in numbered if i not in picked][: 5 - len(picked)]

    def upper(name: str) -> str:
        return " ".join(name.upper().split())

    entries: list[tuple[str, Decimal, Decimal]] = []  # narration, debit, credit
    for index, invoice in enumerate(picked):
        name, ref = upper(invoice.customer_name), f"{invoice.id:06d}"
        if index == 0:
            entries.append((f"NEFT CR-HDFC0{ref}-{name}-{invoice.number}", Decimal(0), invoice.outstanding))
        elif index == 1:
            half = (invoice.outstanding / 2).quantize(CENT)
            entries.append((f"UPI/{ref}31/{name}/PAYMENT {invoice.number}", Decimal(0), half))
        elif index == 2:
            entries.append((f"IMPS-{ref}-{invoice.number.replace('-', '')}", Decimal(0), invoice.outstanding))
        elif index == 3:
            entries.append((f"NEFT CR-ICIC0{ref}-{name}-SUBSCRIPTION", Decimal(0), invoice.outstanding))
        else:
            entries.append((f"CHQ DEP {ref} {name} {invoice.number}", Decimal(0), invoice.outstanding))
        if index == 1:
            entries.append(("ATM WDL-302 MG ROAD BENGALURU", Decimal("5000.00"), Decimal(0)))
    entries.append(("NEFT CR-SBIN0004567-RAVI KUMAR-REFUND", Decimal(0), Decimal("2499.00")))
    entries.append(("SMS ALERT CHARGES", Decimal("17.70"), Decimal(0)))

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Brightloop Software Pvt Ltd - Current Account XXXXXX4821"])
    writer.writerow([f"Statement from {(today - timedelta(days=len(entries))):%d/%m/%Y} to {today:%d/%m/%Y}"])
    writer.writerow([])
    writer.writerow(
        ["Date", "Narration", "Chq./Ref.No.", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"]
    )
    balance = Decimal("250000.00")
    for offset, (narration, debit, credit) in enumerate(entries):
        balance += credit - debit
        when = today - timedelta(days=len(entries) - 1 - offset)
        writer.writerow(
            [
                f"{when:%d/%m/%Y}",
                narration,
                f"{900000 + offset:012d}",
                f"{debit:,.2f}" if debit else "",
                f"{credit:,.2f}" if credit else "",
                f"{balance:,.2f}",
            ]
        )
    return out.getvalue()
