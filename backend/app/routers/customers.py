"""Owner: B — customer records (admin + staff). A customer may exist without a portal login."""

from fastapi import APIRouter, status
from sqlalchemy import func, or_, select

from app.core.csv_export import csv_response
from app.core.deps import Db, StaffUser
from app.core.errors import Conflict
from app.core.lookup import get_or_404
from app.core.pagination import Page, Pages, like_pattern, paginate
from app.models import Customer, Subscription
from app.routers.reports import ReportFilters
from app.routers.reports import summary as report_summary
from app.schemas.people import CustomerIn, CustomerOut
from app.services.customer_views import CustomerOverview, customer_overview

router = APIRouter(prefix="/api/customers", tags=["customers"])


def customer_out(c: Customer) -> CustomerOut:
    return CustomerOut(
        id=c.id,
        name=c.name,
        email=c.email,
        phone=c.phone,
        address=c.address,
        has_login=c.user_id is not None,
        created_at=c.created_at,
    )


def _search(q: str | None):
    stmt = select(Customer).order_by(Customer.name, Customer.id)
    if q and q.strip():
        like = like_pattern(q)
        stmt = stmt.where(
            or_(Customer.name.ilike(like, escape="\\"), Customer.email.ilike(like, escape="\\"))
        )
    return stmt


@router.get("", response_model=Page[CustomerOut])
def list_customers(db: Db, _: StaffUser, pages: Pages, q: str | None = None):
    rows, total = paginate(db, _search(q), pages)
    return Page(
        items=[customer_out(c) for c in rows], total=total, page=pages.page, page_size=pages.page_size
    )


@router.get("/export.csv")
def export_customers(db: Db, _: StaffUser, q: str | None = None):
    rows = (
        (c.name, c.email, c.phone, c.address, "yes" if c.user_id else "no", c.created_at.date())
        for c in db.scalars(_search(q))
    )
    return csv_response("customers", ["Name", "Email", "Phone", "Address", "Portal login", "Created"], rows)


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerIn, db: Db, _: StaffUser):
    customer = Customer(**body.model_dump())
    db.add(customer)
    db.commit()
    return customer_out(customer)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Db, _: StaffUser):
    return customer_out(get_or_404(db, Customer, customer_id))


@router.get("/{customer_id}/overview", response_model=CustomerOverview)
def get_customer_overview(customer_id: int, db: Db, user: StaffUser):
    customer = get_or_404(db, Customer, customer_id)
    summary = report_summary(db, user, ReportFilters(customer_id=customer_id))
    return customer_overview(db, customer, customer_out(customer), summary)


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, body: CustomerIn, db: Db, _: StaffUser):
    customer = get_or_404(db, Customer, customer_id)
    for field, value in body.model_dump().items():
        setattr(customer, field, value)
    db.commit()
    return customer_out(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, db: Db, _: StaffUser):
    customer = get_or_404(db, Customer, customer_id)
    if customer.user_id is not None:
        raise Conflict("This customer has a portal login, so it can't be deleted.")
    if db.scalar(
        select(func.count()).select_from(Subscription).where(Subscription.customer_id == customer_id)
    ):
        raise Conflict("This customer has subscriptions, so it can't be deleted.")
    db.delete(customer)
    db.commit()
