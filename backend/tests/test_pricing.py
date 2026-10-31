from decimal import Decimal as D

from app.enums import AmountKind, BillingPeriod
from app.services.dates import add_period
from app.services.pricing import DiscountRule, TaxRule, compute_line, compute_totals

PCT, FIXED = AmountKind.PERCENT, AmountKind.FIXED


def test_variant_extra_is_added_to_unit_price():  # Odoo brand +560
    r = compute_line(D(1000), 2, variant_extra=D(560))
    assert (r.unit_price, r.subtotal, r.total) == (D("1560.00"), D("3120.00"), D("3120.00"))


def test_percent_discount_applies_before_percent_tax():
    r = compute_line(D(100), 10, taxes=[TaxRule(PCT, D(18))], discount=DiscountRule(PCT, D(10)))
    assert (r.discount_amount, r.tax_amount, r.total) == (D("100.00"), D("162.00"), D("1062.00"))


def test_fixed_discount_is_capped_at_subtotal():
    r = compute_line(D(50), 1, discount=DiscountRule(FIXED, D(80)))
    assert (r.discount_amount, r.total) == (D("50.00"), D("0.00"))


def test_multiple_taxes_fixed_tax_is_per_unit():
    r = compute_line(D(200), 3, taxes=[TaxRule(PCT, D(9)), TaxRule(FIXED, D(5))])
    assert (r.tax_amount, r.total) == (D("69.00"), D("669.00"))


def test_rounding_is_half_up():
    assert compute_line(D("0.05"), 1, taxes=[TaxRule(PCT, D(50))]).tax_amount == D("0.03")


def test_totals_sum_lines():
    a = compute_line(D(10), 1, taxes=[TaxRule(PCT, D(10))])
    b = compute_line(D(20), 2, discount=DiscountRule(FIXED, D(5)))
    t = compute_totals([a, b])
    assert (t.subtotal, t.discount_total, t.tax_total, t.total) == (
        D("50.00"),
        D("5.00"),
        D("1.00"),
        D("46.00"),
    )


def test_add_period_clamps_month_end():
    from datetime import date

    assert add_period(date(2026, 1, 31), BillingPeriod.MONTHLY) == date(2026, 2, 28)
    assert add_period(date(2028, 2, 29), BillingPeriod.YEARLY) == date(2029, 2, 28)
    assert add_period(date(2026, 12, 15), BillingPeriod.MONTHLY) == date(2027, 1, 15)
    assert add_period(date(2026, 1, 1), BillingPeriod.WEEKLY) == date(2026, 1, 8)
