import os

# Point the app at the test database BEFORE importing anything from `app`.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://localhost:5432/brightloop_test"
)

os.environ["SCHEDULER_ENABLED"] = "false"  # tests call the daily jobs directly

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db import get_db  # noqa: E402
from app.enums import Role  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Customer, User  # noqa: E402

engine = create_engine(os.environ["DATABASE_URL"])


@pytest.fixture(scope="session", autouse=True)
def schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db():
    """Each test runs in a transaction that is rolled back, so tests never see each other's data."""
    conn = engine.connect()
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    outer.rollback()
    conn.close()


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def users(db):
    """admin / staff / customer (with a linked Customer row), all with password 'Passw0rd!x'."""
    pw = hash_password("Passw0rd!x")
    made = {
        "admin": User(email="admin@t.test", name="Admin", role=Role.ADMIN, password_hash=pw),
        "staff": User(email="staff@t.test", name="Staff", role=Role.STAFF, password_hash=pw),
        "customer": User(email="cust@t.test", name="Cust", role=Role.CUSTOMER, password_hash=pw),
    }
    db.add_all(made.values())
    db.flush()
    db.add(Customer(name="Cust Co", email="cust@t.test", user_id=made["customer"].id))
    db.commit()  # commit (not flush) so a later rollback inside a request can't undo the fixture
    return made


@pytest.fixture()
def login(client):
    """login("staff@t.test") signs the test client in and returns the response."""

    def _login(email: str, password: str = "Passw0rd!x"):
        return client.post("/api/auth/login", json={"email": email, "password": password})

    return _login


@pytest.fixture()
def catalog(db, users):
    """A product (Odoo variant +560, 18% tax), three plans and the customer linked to cust@t.test."""
    from datetime import date, timedelta
    from types import SimpleNamespace

    from sqlalchemy import select

    from app.enums import AmountKind, BillingPeriod
    from app.models import Plan, Product, ProductVariant, Tax

    gst = Tax(name="GST 18%", kind=AmountKind.PERCENT, rate=18)
    odoo = ProductVariant(attribute="Brand", value="Odoo", extra_price=560)
    standard = ProductVariant(attribute="Brand", value="Standard", extra_price=0)
    crm = Product(
        name="CRM", sales_price=1000, cost_price=200, default_taxes=[gst], variants=[standard, odoo]
    )
    other = Product(
        name="Other", sales_price=50, variants=[ProductVariant(attribute="Size", value="XL", extra_price=5)]
    )
    # Everything allowed.
    monthly = Plan(
        name="Monthly",
        price=0,
        billing_period=BillingPeriod.MONTHLY,
        pausable=True,
        closable=True,
        renewable=True,
    )
    # Nothing allowed: no pause, no early close, no renewal; auto-closes; each line needs 5+.
    strict = Plan(
        name="Strict yearly",
        price=0,
        billing_period=BillingPeriod.YEARLY,
        min_quantity=5,
        pausable=False,
        closable=False,
        renewable=False,
        auto_close=True,
    )
    ended = Plan(
        name="Ended",
        price=0,
        billing_period=BillingPeriod.MONTHLY,
        available_to=date.today() - timedelta(days=1),
    )
    db.add_all([gst, crm, other, monthly, strict, ended])
    db.commit()
    from app.models import Customer

    customer = db.scalar(select(Customer).where(Customer.email == "cust@t.test"))
    return SimpleNamespace(
        gst=gst,
        crm=crm,
        other=other,
        odoo=odoo,
        standard=standard,
        monthly=monthly,
        strict=strict,
        ended=ended,
        customer=customer,
    )
