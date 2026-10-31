from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.enums import AmountKind, BillingPeriod, ProductType
from app.schemas.common import MoneyIn, Name, OptionalText, blank_to_none


class TaxBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: AmountKind
    rate: Decimal


class VariantIn(BaseModel):
    id: int | None = None  # present = update that variant, absent = new one
    attribute: Name  # e.g. "Brand"
    value: Name  # e.g. "Odoo"
    extra_price: MoneyIn = Decimal("0")  # e.g. 560 added to the price when chosen


class VariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attribute: str
    value: str
    extra_price: Decimal


class ProductIn(BaseModel):
    name: Name
    type: ProductType = ProductType.SERVICE
    sales_price: MoneyIn
    cost_price: MoneyIn = Decimal("0")
    notes: OptionalText = None
    active: bool = True
    variants: list[VariantIn] = []
    default_tax_ids: list[int] = []

    _blank = field_validator("notes")(blank_to_none)

    @model_validator(mode="after")
    def unique_variants(self):
        seen = set()
        for v in self.variants:
            key = (v.attribute.lower(), v.value.lower())
            if key in seen:
                raise ValueError(f"Variant {v.attribute}: {v.value} is listed twice.")
            seen.add(key)
        return self


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: ProductType
    sales_price: Decimal
    cost_price: Decimal
    notes: str | None
    active: bool
    variants: list[VariantOut]
    default_taxes: list[TaxBrief]
    created_at: datetime


class PlanIn(BaseModel):
    name: Name
    price: MoneyIn
    billing_period: BillingPeriod
    min_quantity: int = 1
    available_from: date | None = None
    available_to: date | None = None
    auto_close: bool = False  # closes by itself when it ends
    closable: bool = True  # can be closed early
    pausable: bool = False
    renewable: bool = True
    active: bool = True

    @field_validator("min_quantity")
    @classmethod
    def at_least_one(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Minimum quantity must be at least 1.")
        return v

    @model_validator(mode="after")
    def window_is_ordered(self):
        if self.available_from and self.available_to and self.available_to < self.available_from:
            raise ValueError("The plan can't end before it starts.")
        return self


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: Decimal
    billing_period: BillingPeriod
    min_quantity: int
    available_from: date | None
    available_to: date | None
    auto_close: bool
    closable: bool
    pausable: bool
    renewable: bool
    active: bool
    created_at: datetime
