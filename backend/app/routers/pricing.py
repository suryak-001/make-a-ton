"""Owner: A — line price preview, so forms show the same numbers the backend will store.
The frontend never re-implements pricing math; it calls this."""

from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser
from app.enums import AmountKind
from app.services.pricing import DiscountRule, TaxRule, compute_line

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


class TaxIn(BaseModel):
    kind: AmountKind
    rate: Decimal = Field(ge=0)


class DiscountIn(BaseModel):
    kind: AmountKind
    value: Decimal = Field(ge=0)


class PreviewIn(BaseModel):
    unit_price: Decimal = Field(ge=0)
    quantity: int = Field(ge=1)
    variant_extra: Decimal = Decimal("0")
    taxes: list[TaxIn] = []
    discount: DiscountIn | None = None


class PreviewOut(BaseModel):
    unit_price: Decimal
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total: Decimal


@router.post("/preview", response_model=PreviewOut)
def preview(body: PreviewIn, _: CurrentUser):
    r = compute_line(
        body.unit_price,
        body.quantity,
        body.variant_extra,
        [TaxRule(t.kind, t.rate) for t in body.taxes],
        DiscountRule(body.discount.kind, body.discount.value) if body.discount else None,
    )
    return PreviewOut(**vars(r))
