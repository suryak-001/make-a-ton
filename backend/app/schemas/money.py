from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.enums import AmountKind, DiscountScope, InvoiceStatus, PaymentMethod
from app.schemas.common import MoneyIn, Name, OptionalText, blank_to_none


class TaxIn(BaseModel):
    name: Name
    kind: AmountKind
    rate: MoneyIn
    active: bool = True


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

    @model_validator(mode="after")
    def valid_rule(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("The discount can't end before it starts.")
        if self.kind == AmountKind.PERCENT and self.value > 100:
            raise ValueError("A percentage discount can't exceed 100%.")
        if self.scope == DiscountScope.PRODUCT and not self.product_ids:
            raise ValueError("Select at least one product for a product discount.")
        if self.scope == DiscountScope.SUBSCRIPTION and not self.subscription_ids:
            raise ValueError("Select at least one subscription for a subscription discount.")
        return self


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
    lines: list[InvoiceLineOut] = []


class BillingRunIn(BaseModel):
    as_of: date | None = None


class BillingRunOut(BaseModel):
    created: int
    skipped: int
    errors: list[dict]


class PaymentIn(BaseModel):
    invoice_id: int
    method: PaymentMethod
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    payment_date: date
    note: OptionalText = None

    def model_post_init(self, __context) -> None:
        self.note = blank_to_none(self.note)


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
