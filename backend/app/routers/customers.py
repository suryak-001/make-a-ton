"""Owner: B — customer records (admin + staff). A customer may exist without a portal login."""

from fastapi import APIRouter, status
from sqlalchemy import func, or_, select

from app.core.deps import Db, StaffUser
from app.core.errors import Conflict
from app.core.lookup import get_or_404
from app.core.pagination import Page, Pages, like_pattern, paginate
from app.models import Customer, Subscription
from app.schemas.people import CustomerIn, CustomerOut

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


@router.get("", response_model=Page[CustomerOut])
def list_customers(db: Db, _: StaffUser, pages: Pages, q: str | None = None):
    stmt = select(Customer).order_by(Customer.name, Customer.id)
    if q and q.strip():
        like = like_pattern(q)
        stmt = stmt.where(
            or_(Customer.name.ilike(like, escape="\\"), Customer.email.ilike(like, escape="\\"))
        )
    rows, total = paginate(db, stmt, pages)
    return Page(
        items=[customer_out(c) for c in rows], total=total, page=pages.page, page_size=pages.page_size
    )


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerIn, db: Db, _: StaffUser):
    customer = Customer(**body.model_dump())
    db.add(customer)
    db.commit()
    return customer_out(customer)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Db, _: StaffUser):
    return customer_out(get_or_404(db, Customer, customer_id))


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
