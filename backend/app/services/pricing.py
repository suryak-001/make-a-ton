"""Owner: A. Pure functions, no DB access. Both tracks use these so quotes and invoices agree."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.enums import AmountKind

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def round2(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class TaxRule:
    kind: AmountKind
    rate: Decimal


@dataclass(frozen=True)
class DiscountRule:
    kind: AmountKind
    value: Decimal


@dataclass(frozen=True)
class LineResult:
    unit_price: Decimal  # unit price + variant extra
    subtotal: Decimal  # before discount and tax
    discount_amount: Decimal
    tax_amount: Decimal
    total: Decimal


@dataclass(frozen=True)
class Totals:
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal


def compute_line(
    unit_price: Decimal,
    quantity: int,
    variant_extra: Decimal = ZERO,
    taxes: list[TaxRule] | None = None,
    discount: DiscountRule | None = None,
) -> LineResult:
    effective_unit = round2(unit_price + variant_extra)
    subtotal = round2(effective_unit * quantity)

    discount_amount = ZERO
    if discount is not None:
        raw = subtotal * discount.value / 100 if discount.kind == AmountKind.PERCENT else discount.value
        discount_amount = min(round2(raw), subtotal)

    # Taxes apply to the discounted amount. FIXED taxes are per unit.
    taxable = subtotal - discount_amount
    tax_amount = round2(
        sum(
            (
                taxable * t.rate / 100 if t.kind == AmountKind.PERCENT else t.rate * quantity
                for t in taxes or []
            ),
            start=ZERO,
        )
    )
    return LineResult(effective_unit, subtotal, discount_amount, tax_amount, round2(taxable + tax_amount))


def compute_totals(lines: list[LineResult]) -> Totals:
    return Totals(
        subtotal=round2(sum((x.subtotal for x in lines), start=ZERO)),
        discount_total=round2(sum((x.discount_amount for x in lines), start=ZERO)),
        tax_total=round2(sum((x.tax_amount for x in lines), start=ZERO)),
        total=round2(sum((x.total for x in lines), start=ZERO)),
    )
