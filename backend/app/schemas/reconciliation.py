from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.enums import PaymentMethod

Ref = Field(pattern=r"^[0-9a-f]{64}$")


class StatementIn(BaseModel):
    csv: str = Field(min_length=1, max_length=2_000_000)  # the file's text; the browser reads it


class InvoiceHint(BaseModel):
    id: int
    number: str
    customer_name: str
    outstanding: Decimal
    due_date: date


class StatementRowOut(BaseModel):
    ref: str  # fingerprint of the statement line, stored on the payment it becomes
    line: int  # row number in the file
    date: date
    description: str
    amount: Decimal
    method: PaymentMethod  # guessed from the narration (UPI, NEFT, cheque, card…)
    status: Literal["matched", "unmatched", "already_recorded"]
    confidence: Literal["high", "medium", "low"] | None
    reason: str
    invoice: InvoiceHint | None


class StatementProblem(BaseModel):
    line: int
    error: str


class PreviewOut(BaseModel):
    rows: list[StatementRowOut]  # credits only
    debits_skipped: int
    problems: list[StatementProblem]


class ApplyItemIn(BaseModel):
    ref: str = Ref
    invoice_id: int
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    payment_date: date
    method: PaymentMethod
    description: str = Field(max_length=480)


class ApplyIn(BaseModel):
    items: list[ApplyItemIn] = Field(min_length=1, max_length=2000)


class ApplyResultOut(BaseModel):
    ref: str
    status: Literal["recorded", "already_recorded", "failed"]
    message: str
    invoice_number: str | None


class ApplyOut(BaseModel):
    recorded: int
    already_recorded: int
    failed: int
    amount_recorded: Decimal
    results: list[ApplyResultOut]
