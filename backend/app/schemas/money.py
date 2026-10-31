from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.enums import AmountKind, DiscountScope, InvoiceStatus, PaymentMethod
from app.schemas.common import MoneyIn, Name, OptionalText, blank_to_none


class TaxIn(BaseModel):
    name: Name
    kind: AmountKind = AmountKind.PERCENT
    rate: MoneyIn  # 18 = 18% when PERCENT; an amount per unit when FIXED
    active: bool = True

    @field_validator("rate")
    @classmethod
    def percent_is_at_most_100(cls, rate: Decimal, info: ValidationInfo) -> Decimal:
        if info.data.get("kind") == AmountKind.PERCENT and rate > 100:
            raise ValueError("A percentage tax can't be more than 100.")
        return rate


class TaxOut(TaxIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class DiscountIn(BaseModel):
    name: Name
    kind: AmountKind
    value: MoneyIn
    min_purchase: MoneyIn | None = None
    min_quantity: int | None = Field(None, ge=1)
    start_date: date
    end_date: date | None = None
    usage_limit: int | None = Field(None, ge=1)
    scope: DiscountScope
    active: bool = True
    product_ids: list[int] = []
    subscription_ids: list[int] = []

    @field_validator("value")
    @classmethod
    def percent_is_at_most_100(cls, value: Decimal, info: ValidationInfo) -> Decimal:
        if info.data.get("kind") == AmountKind.PERCENT and value > 100:
            raise ValueError("A percentage discount can't exceed 100%.")
        return value

    @field_validator("end_date")
    @classmethod
    def ends_after_it_starts(cls, end_date: date | None, info: ValidationInfo) -> date | None:
        start_date = info.data.get("start_date")
        if end_date and start_date and end_date < start_date:
            raise ValueError("The discount can't end before it starts.")
        return end_date


class DiscountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    kind: AmountKind
    value: Decimal
    min_purchase: Decimal | None
    min_quantity: int | None
    start_date: date
    end_date: date | None
    usage_limit: int | None
    used_count: int
    scope: DiscountScope
    active: bool
    product_ids: list[int]
    subscription_ids: list[int]
    created_at: datetime


class InvoiceLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int | None
    description: str
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal


class CustomerBrief(BaseModel):
    id: int
    name: str
    email: str


class SubscriptionBrief(BaseModel):
    id: int
    number: str


class InvoiceOut(BaseModel):
    id: int
    number: str | None
    status: InvoiceStatus
    subscription: SubscriptionBrief
    customer: CustomerBrief
    period_start: date
    period_end: date
    invoice_date: date
    due_date: date
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    amount_paid: Decimal
    outstanding: Decimal
    overdue: bool
    sent_at: datetime | None
    created_at: datetime
    allowed_actions: list[str]
    lines: list[InvoiceLineOut] = []


class BillingRunIn(BaseModel):
    as_of: date | None = None


class BillingRunOut(BaseModel):
    """`due = created + already_billed + skipped + failed` always holds (docs/API_CONTRACT.md)."""

    as_of: date
    due: int  # billing periods that were due on or before `as_of`
    created: int
    already_billed: int  # the invoice for that period already existed
    skipped: int  # not attempted: an earlier period of the same subscription failed, so it stays due
    failed: int
    errors: list[dict]


class PaymentIn(BaseModel):
    invoice_id: int
    method: PaymentMethod
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    payment_date: date
    note: OptionalText = None

    def model_post_init(self, __context) -> None:
        self.note = blank_to_none(self.note)

    @field_validator("payment_date")
    @classmethod
    def not_in_the_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("The payment date can't be in the future.")
        return v


class PaymentOut(BaseModel):
    id: int
    invoice_id: int
    invoice_number: str | None
    customer_name: str
    method: PaymentMethod
    amount: Decimal
    payment_date: date
    note: str | None
    recorded_by: str | None
    created_at: datetime


class SummaryOut(BaseModel):
    active_subscriptions: int
    mrr: Decimal
    invoiced: Decimal
    collected: Decimal
    outstanding: Decimal
    overdue_count: int
    overdue_amount: Decimal


class RevenuePoint(BaseModel):
    month: str
    invoiced: Decimal
    collected: Decimal
