"""The billing run, invoice generation and the discount rules applied to invoices."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.enums import AmountKind, BillingPeriod, DiscountScope, SubscriptionStatus
from app.models import (
    Base,
    Customer,
    Discount,
    DiscountUsage,
    Invoice,
    Plan,
    Product,
    Subscription,
    SubscriptionLine,
)
from app.services.billing import generate_invoice_for_period, run_billing
from tests.conftest import engine

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)


def make_sub(db, catalog, *, number="SUB-T-1", start=date(2026, 1, 31), with_lines=True) -> Subscription:
    """An ACTIVE monthly subscription: 2 x CRM (Odoo) = 3120.00 + 18% tax, billed from `start`."""
    lines = [
        SubscriptionLine(
            product_id=catalog.crm.id,
            variant_id=catalog.odoo.id,
            quantity=2,
            unit_price=Decimal("1560"),
            amount=Decimal("3681.60"),
            taxes=[catalog.gst],
        )
    ]
    sub = Subscription(
        number=number,
        customer_id=catalog.customer.id,
        plan_id=catalog.monthly.id,
        status=SubscriptionStatus.ACTIVE,
        start_date=start,
        next_invoice_date=start,
        lines=lines if with_lines else [],
    )
    db.add(sub)
    db.commit()
    return sub


def make_discount(db, scope, *, subscription=None, product=None, **over) -> Discount:
    values = {
        "name": "Ten off",
        "kind": AmountKind.PERCENT,
        "value": Decimal("10"),
        "start_date": YESTERDAY,
        "scope": scope,
        "subscriptions": [subscription] if subscription else [],
        "products": [product] if product else [],
    }
    discount = Discount(**{**values, **over})
    db.add(discount)
    db.commit()
    return discount


def assert_adds_up(result):
    assert result.due == result.created + result.already_billed + result.skipped + result.failed


# ───────────────────────────── the billing run ─────────────────────────────


def test_three_periods_behind_bills_exactly_three_and_a_rerun_bills_none(db, catalog):
    make_sub(db, catalog)
    first = run_billing(db, date(2026, 3, 31))
    assert (first.due, first.created) == (3, 3)
    assert_adds_up(first)
    again = run_billing(db, date(2026, 3, 31))
    assert (again.due, again.created) == (0, 0)


def test_a_period_that_already_has_an_invoice_is_counted_not_duplicated(db, catalog):
    sub = make_sub(db, catalog)
    generate_invoice_for_period(db, sub.id, sub.start_date)
    db.commit()
    result = run_billing(db, sub.start_date)
    assert (result.due, result.created, result.already_billed) == (1, 0, 1)
    assert db.scalar(select(func.count()).select_from(Invoice)) == 1
    assert sub.next_invoice_date == date(2026, 2, 28)


def test_a_failing_subscription_is_recorded_stays_due_and_the_run_continues(db, catalog):
    broken = make_sub(db, catalog, number="SUB-BROKEN", with_lines=False)
    make_sub(db, catalog, number="SUB-GOOD")
    result = run_billing(db, date(2026, 3, 31))
    assert (result.due, result.created, result.failed, result.skipped) == (6, 3, 1, 2)
    assert_adds_up(result)
    assert result.errors[0]["subscription_id"] == broken.id
    db.refresh(broken)
    assert broken.next_invoice_date == date(2026, 1, 31)


def test_staff_can_run_billing_through_the_api_and_customers_cannot(client, login, db, catalog, users):
    make_sub(db, catalog, start=TODAY)
    login("cust@t.test")
    assert client.post("/api/invoices/run-billing", json={}).status_code == 403
    login("staff@t.test")
    body = client.post("/api/invoices/run-billing", json={}).json()
    assert (body["due"], body["created"], body["failed"]) == (1, 1, 0)
    assert body["as_of"] == str(TODAY) and body["errors"] == []


def test_a_paused_subscription_is_not_billed(db, catalog):
    sub = make_sub(db, catalog)
    sub.status = SubscriptionStatus.PAUSED
    db.commit()
    assert run_billing(db, date(2026, 3, 31)).due == 0


# ───────────────────────────── discounts on the invoice ─────────────────────────────


def test_a_subscription_discount_lowers_the_tax_too(db, catalog):
    sub = make_sub(db, catalog, start=TODAY)
    make_discount(db, DiscountScope.SUBSCRIPTION, subscription=sub)
    invoice = generate_invoice_for_period(db, sub.id, TODAY)
    assert invoice.subtotal == Decimal("3120.00")
    assert invoice.discount_total == Decimal("312.00")
    assert invoice.tax_total == Decimal("505.44")  # 18% of 2808.00, not of 3120.00
    assert invoice.total == Decimal("3313.44")
    assert sum(line.discount_amount for line in invoice.lines) == invoice.discount_total


def test_a_fixed_product_discount_comes_off_the_matching_line_before_tax(db, catalog):
    sub = make_sub(db, catalog, start=TODAY)
    make_discount(db, DiscountScope.PRODUCT, product=catalog.crm, kind=AmountKind.FIXED, value=Decimal("100"))
    invoice = generate_invoice_for_period(db, sub.id, TODAY)
    assert invoice.discount_total == Decimal("100.00")
    assert invoice.tax_total == Decimal("543.60")  # 18% of 3020.00
    assert invoice.total == Decimal("3563.60")


def test_a_discount_never_takes_an_invoice_below_zero(db, catalog):
    sub = make_sub(db, catalog, start=TODAY)
    make_discount(
        db, DiscountScope.SUBSCRIPTION, subscription=sub, kind=AmountKind.FIXED, value=Decimal("99999")
    )
    invoice = generate_invoice_for_period(db, sub.id, TODAY)
    assert (invoice.discount_total, invoice.tax_total, invoice.total) == (
        Decimal("3120.00"),
        Decimal("0.00"),
        Decimal("0.00"),
    )


def test_an_expired_discount_is_not_applied(db, catalog):
    sub = make_sub(db, catalog, start=TODAY)
    make_discount(db, DiscountScope.SUBSCRIPTION, subscription=sub, end_date=YESTERDAY)
    assert generate_invoice_for_period(db, sub.id, TODAY).discount_total == Decimal("0")


def test_the_usage_limit_stops_a_discount_and_each_use_is_recorded(db, catalog):
    first = make_sub(db, catalog, number="SUB-T-1", start=TODAY)
    second = make_sub(db, catalog, number="SUB-T-2", start=TODAY)
    discount = make_discount(db, DiscountScope.PRODUCT, product=catalog.crm, usage_limit=1)
    assert generate_invoice_for_period(db, first.id, TODAY).discount_total > 0
    assert generate_invoice_for_period(db, second.id, TODAY).discount_total == 0
    db.refresh(discount)
    assert discount.used_count == 1
    assert db.scalar(select(func.count()).select_from(DiscountUsage)) == 1


# ───────────────────────────── concurrency (real, committed sessions) ─────────────────────────────

CONCURRENT_INVOICES = 20
USAGE_LIMIT = 5


def seed_committed_subscriptions() -> list[int]:
    with Session(engine) as session:
        customer = Customer(name="Racer", email="racer@t.test")
        plan = Plan(name="Monthly", price=0, billing_period=BillingPeriod.MONTHLY)
        product = Product(name="Seat", sales_price=100)
        session.add_all([customer, plan, product])
        session.flush()
        session.add(
            Discount(
                name="Limited",
                kind=AmountKind.PERCENT,
                value=10,
                start_date=YESTERDAY,
                usage_limit=USAGE_LIMIT,
                scope=DiscountScope.PRODUCT,
                products=[product],
            )
        )
        subs = [
            Subscription(
                number=f"SUB-RACE-{i}",
                customer_id=customer.id,
                plan_id=plan.id,
                status=SubscriptionStatus.ACTIVE,
                start_date=TODAY,
                next_invoice_date=TODAY,
                lines=[
                    SubscriptionLine(product_id=product.id, quantity=1, unit_price=Decimal("100"), amount=100)
                ],
            )
            for i in range(CONCURRENT_INVOICES)
        ]
        session.add_all(subs)
        session.commit()
        return [sub.id for sub in subs]


def bill_in_its_own_session(subscription_id: int) -> None:
    with Session(engine) as session:
        generate_invoice_for_period(session, subscription_id, TODAY)
        session.commit()


def truncate_everything() -> None:
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


def test_twenty_concurrent_invoices_use_a_limit_five_discount_exactly_five_times():
    subscription_ids = seed_committed_subscriptions()
    try:
        with ThreadPoolExecutor(max_workers=CONCURRENT_INVOICES) as pool:
            list(pool.map(bill_in_its_own_session, subscription_ids))
        with Session(engine) as session:
            used_count = session.scalar(select(Discount.used_count))
            usages = session.scalar(select(func.count()).select_from(DiscountUsage))
            discounted = session.scalar(select(func.count()).where(Invoice.discount_total > 0))
            invoices = session.scalar(select(func.count()).select_from(Invoice))
        assert (used_count, usages, discounted, invoices) == (USAGE_LIMIT, USAGE_LIMIT, USAGE_LIMIT, 20)
    finally:
        truncate_everything()
