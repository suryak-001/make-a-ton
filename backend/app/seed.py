"""Dev seed: wipes and recreates demo data.  Run: `uv run python -m app.seed`

SHARED FILE: Person A edits the catalog/subscription sections, Person B edits the rules/billing sections.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text

from app.core.security import hash_password
from app.db import SessionLocal
from app.enums import AmountKind, BillingPeriod, DiscountScope, ProductType, Role, SubscriptionStatus
from app.models import (
    Customer,
    Discount,
    Plan,
    Product,
    ProductVariant,
    QuotationTemplate,
    QuotationTemplateLine,
    Subscription,
    SubscriptionLine,
    Tax,
    User,
)
from app.services.pricing import TaxRule, compute_line
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


def main() -> None:
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

        # ── Section B: taxes ──
        gst18 = Tax(name="GST 18%", kind=AmountKind.PERCENT, rate=D(18))
        db.add_all([gst18, Tax(name="GST 5%", kind=AmountKind.PERCENT, rate=D(5))])

        # ── Section A: customers, catalog, plans, templates ──
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
            name="Analytics add-on", sales_price=D(400), cost_price=D(80), default_taxes=[gst18]
        )
        support = Product(
            name="Priority support", sales_price=D(800), cost_price=D(200), default_taxes=[gst18]
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
                    QuotationTemplateLine(product_id=support.id, quantity=1),
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

        S = SubscriptionStatus
        # Started 60 days ago, monthly → two periods due, exercises billing catch-up.
        subscription(acme, monthly, S.ACTIVE, days(-60), [(crm, None, 3), (analytics, None, 1)])
        subscription(
            globex, yearly, S.ACTIVE, days(-10), [(crm, odoo, 12), (support, None, 1)], expiry=days(355)
        )
        subscription(northwind, monthly, S.QUOTATION, days(7), [(crm, None, 5)])
        subscription(northwind, monthly, S.DRAFT, days(14), [(analytics, None, 2)])

        # ── Section B: discounts (invoices/payments come from the billing run) ──
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
    print(
        "Seeded. Logins: admin@brightloop.test / Admin@12345, staff@brightloop.test / Staff@12345, priya@acme.test / Customer@123"
    )


if __name__ == "__main__":
    main()
