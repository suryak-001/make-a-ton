from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.enums import AmountKind, BillingPeriod, SubscriptionStatus
from app.schemas.common import OptionalText, blank_to_none


class LineIn(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(ge=1)


class SubscriptionIn(BaseModel):
    customer_id: int
    plan_id: int
    start_date: date
    expiry_date: date | None = None
    payment_term_days: int = Field(15, ge=0, le=365)
    validity_days: int = Field(30, ge=1, le=365)  # how long the quote stays valid once sent
    notes: OptionalText = None
    lines: list[LineIn] = Field(min_length=1)

    def model_post_init(self, __context) -> None:
        self.notes = blank_to_none(self.notes)


Reason = Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=500)]


class TransitionIn(BaseModel):
    to: SubscriptionStatus
    reason: Reason = None


class RenewIn(BaseModel):
    reason: Reason = None


class FromTemplateIn(BaseModel):
    customer_id: int
    start_date: date | None = None  # defaults to today
    expiry_date: date | None = None
    payment_term_days: int = Field(15, ge=0, le=365)


class Brief(BaseModel):
    id: int
    name: str


class PlanBrief(Brief):
    billing_period: BillingPeriod


class CustomerBrief(Brief):
    email: str


class SubscriptionListItem(BaseModel):
    id: int
    number: str
    status: SubscriptionStatus
    customer: Brief
    plan: PlanBrief
    start_date: date
    expiry_date: date | None
    total: Decimal


class TaxOut(BaseModel):
    id: int
    name: str
    kind: AmountKind
    rate: Decimal


class LineOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    variant_id: int | None
    variant_label: str | None  # "Brand: Odoo"
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    amount: Decimal
    taxes: list[TaxOut]


class EventOut(BaseModel):
    id: int
    from_status: SubscriptionStatus | None
    to_status: SubscriptionStatus
    reason: str | None
    actor_name: str | None  # None for the lifecycle job, and always hidden from customers
    created_at: datetime


class PlanDetail(PlanBrief):
    min_quantity: int
    pausable: bool
    closable: bool
    renewable: bool
    auto_close: bool


class PortalSubscriptionDetail(BaseModel):
    """What a customer may see about their own subscription (no internal notes or staff names)."""

    id: int
    number: str
    status: SubscriptionStatus
    customer: CustomerBrief
    plan: PlanDetail
    start_date: date
    expiry_date: date | None
    payment_term_days: int
    quotation_valid_until: date | None
    next_invoice_date: date | None
    created_at: datetime
    lines: list[LineOut]
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    events: list[EventOut]
    # Target statuses plus "RENEW" that can be applied right now, already filtered by plan flags.
    allowed_actions: list[str]


class SubscriptionDetail(PortalSubscriptionDetail):
    validity_days: int
    notes: str | None
    created_by: str | None
    editable: bool  # DRAFT and QUOTATION can still be edited


class LifecycleResult(BaseModel):
    closed: int
    expired_quotations: int
