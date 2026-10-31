"""Dev seed: wipes and recreates demo data. Run normally or add ``--big`` for 5,000 subscriptions.

SHARED FILE: Person A edits rules/billing; Person B edits catalog/subscriptions.
"""

import argparse
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, text

from app.core.security import hash_password
from app.db import SessionLocal
from app.enums import (
    AmountKind,
    BillingPeriod,
    DiscountScope,
    InvoiceStatus,
    PaymentMethod,
    ProductType,
    Role,
    SubscriptionStatus,
)
from app.models import (
    Customer,
    Discount,
    Invoice,
    Payment,
    Plan,
    Product,
    ProductVariant,
    QuotationTemplate,
    QuotationTemplateLine,
    Subscription,
    SubscriptionEvent,
    SubscriptionLine,
    Tax,
    User,
)
from app.services.billing import run_billing
from app.services.invoices import confirm_invoice
from app.services.pricing import TaxRule, compute_line, round2
from app.services.sequence import next_number

D = Decimal
today = date.today()


def days(n: int) -> date:
    return today + timedelta(days=n)


def wipe(db) -> None:
    tables = (
        db.execute(
            text(
                "select tablename from pg_tables where schemaname='public' and tablename <> 'alembic_version'"
            )
        )
        .scalars()
        .all()
    )
    db.execute(text("TRUNCATE " + ", ".join(f'"{t}"' for t in tables) + " RESTART IDENTITY CASCADE"))


VOLUME_CUSTOMERS = 200
VOLUME_SUBSCRIPTIONS = 4_995  # with the 5 demo subscriptions this makes 5,000
VOLUME_SPREAD_DAYS = 110  # start dates reach back this far, so billing catches up on several periods
# Share of each invoice paid, repeating down the list: mostly settled, some part-paid, some unpaid.
PAYMENT_PATTERN = [D(1)] * 6 + [D("0.5")] * 2 + [D(0)] * 2


def seed_volume(db, admin, plan, product, tax) -> None:
    """Thousands of active subscriptions across many customers, started over the last few months."""
    customers = [
        Customer(name=f"Customer {n:03d}", email=f"customer{n:03d}@volume.test")
        for n in range(VOLUME_CUSTOMERS)
    ]
    db.add_all(customers)
    db.flush()
    for i in range(VOLUME_SUBSCRIPTIONS):
        start = days(-(i % VOLUME_SPREAD_DAYS))
        quantity = 1 + i % 5
        db.add(
            Subscription(
                number=next_number(db, "SUB", "SUB-"),
                customer_id=customers[i % VOLUME_CUSTOMERS].id,
                plan_id=plan.id,
                status=SubscriptionStatus.ACTIVE,
                start_date=start,
                payment_term_days=15,
                next_invoice_date=start,
                created_by_id=admin.id,
                lines=[
                    SubscriptionLine(
                        product_id=product.id,
                        quantity=quantity,
                        unit_price=product.sales_price,
                        amount=product.sales_price * quantity * D("1.18"),
                        taxes=[tax],
                    )
                ],
            )
        )
        if i % 250 == 0:
            db.flush()
    db.commit()


def confirm_all_invoices(db) -> None:
    for invoice_id in db.scalars(select(Invoice.id).order_by(Invoice.id)).all():
        confirm_invoice(db, invoice_id)
    db.commit()


def add_demo_payment_and_overdue(db, staff) -> None:
    """The small seed: one overdue invoice and one paid invoice, enough to see every state."""
    invoices = list(db.scalars(select(Invoice).order_by(Invoice.id).limit(2)))
    if invoices:
        invoices[0].due_date = days(-10)
    if len(invoices) > 1:
        record_payment(db, invoices[1], invoices[1].total, staff, today, "Seeded paid invoice")


def record_history(db, staff) -> None:
    """The big seed: invoices dated at their period, then payments of varying size spread after them."""
    db.execute(text("UPDATE invoice SET invoice_date = period_start, due_date = period_start + 15"))
    db.expire_all()
    for index, invoice in enumerate(db.scalars(select(Invoice).order_by(Invoice.id)).all()):
        amount = round2(invoice.total * PAYMENT_PATTERN[index % len(PAYMENT_PATTERN)])
        if amount > 0:
            paid_on = min(today, invoice.invoice_date + timedelta(days=index % 20))
            record_payment(db, invoice, amount, staff, paid_on, "Seeded payment")


def record_payment(db, invoice, amount, staff, paid_on, note) -> None:
    db.add(
        Payment(
            invoice_id=invoice.id,
            method=PaymentMethod.BANK_TRANSFER,
            amount=amount,
            payment_date=paid_on,
            note=note,
            recorded_by_id=staff.id,
        )
    )
    invoice.amount_paid += amount
    if invoice.amount_paid >= invoice.total:
        invoice.status = InvoiceStatus.PAID


def main(big: bool = False) -> None:
    with SessionLocal() as db:
        wipe(db)

        # ── Shared: users (passwords meet the policy) ──
        admin = User(
            email="admin@brightloop.test",
            name="Ada Admin",
            role=Role.ADMIN,
            password_hash=hash_password("Admin@12345"),
        )
        staff = User(
            email="staff@brightloop.test",
            name="Sam Staff",
            role=Role.STAFF,
            password_hash=hash_password("Staff@12345"),
        )
        priya = User(
            email="priya@acme.test",
            name="Priya (Acme)",
            role=Role.CUSTOMER,
            password_hash=hash_password("Customer@123"),
        )
        db.add_all([admin, staff, priya])
        db.flush()

        # ── Section A: taxes ──
        gst18 = Tax(name="GST 18%", kind=AmountKind.PERCENT, rate=D(18))
        db.add_all([gst18, Tax(name="GST 5%", kind=AmountKind.PERCENT, rate=D(5))])

        # ── Section B: customers, catalog, plans, templates ──
        acme = Customer(
            name="Acme Retail", email="priya@acme.test", phone="+91 98765 43210", user_id=priya.id
        )
        northwind = Customer(name="Northwind Traders", email="billing@northwind.test")
        globex = Customer(name="Globex Corporation", email="ap@globex.test")
        db.add_all([acme, northwind, globex])

        odoo = ProductVariant(attribute="Brand", value="Odoo", extra_price=D(560))
        crm = Product(
            name="Brightloop CRM",
            type=ProductType.SERVICE,
            sales_price=D(1200),
            cost_price=D(300),
            notes="Per-seat CRM licence",
            default_taxes=[gst18],
            variants=[ProductVariant(attribute="Brand", value="Standard", extra_price=D(0)), odoo],
        )
        analytics = Product(
            name="Analytics add-on",
            sales_price=D(400),
            cost_price=D(80),
            default_taxes=[gst18],
            is_addon=True,
        )
        support = Product(
            name="Priority support",
            sales_price=D(800),
            cost_price=D(200),
            default_taxes=[gst18],
            is_addon=True,
        )
        db.add_all([crm, analytics, support])

        monthly = Plan(
            name="Monthly",
            price=D(0),
            billing_period=BillingPeriod.MONTHLY,
            closable=True,
            pausable=True,
            renewable=True,
        )
        yearly = Plan(
            name="Yearly contract",
            price=D(0),
            billing_period=BillingPeriod.YEARLY,
            min_quantity=5,
            auto_close=True,
            closable=False,
            renewable=True,
        )
        weekly = Plan(
            name="Weekly trial",
            price=D(0),
            billing_period=BillingPeriod.WEEKLY,
            auto_close=True,
            renewable=False,
            available_to=days(90),
        )
        db.add_all([monthly, yearly, weekly])
        db.flush()

        db.add(
            QuotationTemplate(
                name="Enterprise yearly (Odoo)",
                plan_id=yearly.id,
                validity_days=30,
                lines=[
                    QuotationTemplateLine(product_id=crm.id, variant_id=odoo.id, quantity=10),
                    QuotationTemplateLine(product_id=support.id, quantity=5),
                ],
            )
        )

        def subscription(customer, plan, status, start, lines, expiry=None):
            sub = Subscription(
                number=next_number(db, "SUB", "SUB-"),
                customer_id=customer.id,
                plan_id=plan.id,
                status=status,
                start_date=start,
                expiry_date=expiry,
                payment_term_days=15,
                quotation_valid_until=days(30) if status == SubscriptionStatus.QUOTATION else None,
                next_invoice_date=start if status == SubscriptionStatus.ACTIVE else None,
                created_by_id=admin.id,
            )
            for product, variant, qty in lines:
                extra = variant.extra_price if variant else D(0)
                r = compute_line(product.sales_price, qty, extra, [TaxRule(AmountKind.PERCENT, D(18))])
                sub.lines.append(
                    SubscriptionLine(
                        product_id=product.id,
                        variant_id=variant.id if variant else None,
                        quantity=qty,
                        unit_price=r.unit_price,
                        amount=r.total,
                        taxes=[gst18],
                    )
                )
            db.add(sub)
            db.flush()
            # State history, as if the subscription had been walked to its current status by the admin.
            path = {
                S.DRAFT: [],
                S.QUOTATION: [S.QUOTATION],
                S.CONFIRMED: [S.QUOTATION, S.CONFIRMED],
                S.ACTIVE: [S.QUOTATION, S.CONFIRMED, S.ACTIVE],
            }[status]
            previous = None
            for step in [S.DRAFT, *path]:
                db.add(
                    SubscriptionEvent(
                        subscription_id=sub.id, from_status=previous, to_status=step, actor_id=admin.id
                    )
                )
                previous = step
            return sub

        S = SubscriptionStatus
        # Started 60 days ago, monthly → two periods due, exercises billing catch-up.
        subscription(acme, monthly, S.ACTIVE, days(-60), [(crm, None, 3), (analytics, None, 1)])
        subscription(
            globex, yearly, S.ACTIVE, days(-10), [(crm, odoo, 12), (support, None, 5)], expiry=days(355)
        )
        # Starts in 5 days, so nothing is overdue for billing: the customer can pause it in the portal demo.
        subscription(
            acme, monthly, S.ACTIVE, days(5), [(crm, None, 2), (analytics, None, 1)], expiry=days(370)
        )
        subscription(northwind, monthly, S.QUOTATION, days(7), [(crm, None, 5)])
        subscription(northwind, monthly, S.DRAFT, days(14), [(analytics, None, 2)])

        # ── Section A: discounts (invoices/payments come from the billing run) ──
        db.add(
            Discount(
                name="Volume 10% (10+ seats)",
                kind=AmountKind.PERCENT,
                value=D(10),
                min_quantity=10,
                start_date=days(-30),
                end_date=days(90),
                usage_limit=5,
                scope=DiscountScope.PRODUCT,
                products=[crm],
            )
        )

        db.commit()
        if big:
            seed_volume(db, admin, monthly, crm, gst18)

        # Billing, invoice actions, payments and reports all have data straight after seeding.
        run_billing(db, today)
        db.commit()
        confirm_all_invoices(db)
        if big:
            record_history(db, staff)
        else:
            add_demo_payment_and_overdue(db, staff)
        db.commit()
    print(
        "Seeded. Logins: admin@brightloop.test / Admin@12345, staff@brightloop.test / Staff@12345, priya@acme.test / Customer@123"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--big", action="store_true", help="seed 5,000 subscriptions with their invoices and payments"
    )
    main(parser.parse_args().big)
