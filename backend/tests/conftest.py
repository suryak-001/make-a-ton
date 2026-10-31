import os

# Point the app at the test database BEFORE importing anything from `app`.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://localhost:5432/brightloop_test"
)

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
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
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
    db.flush()
    return made
