"""Admin-managed automatic discount rules."""

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import AdminUser, Db
from app.core.errors import Invalid
from app.core.lookup import get_or_404
from app.core.pagination import Page, Pages, like_pattern, paginate
from app.models import Discount, Product, Subscription
from app.schemas.money import DiscountIn, DiscountOut

router = APIRouter(prefix="/api/discounts", tags=["discounts"])

_LOAD = (selectinload(Discount.products), selectinload(Discount.subscriptions))


def _out(d: Discount) -> DiscountOut:
    return DiscountOut(
        **{
            k: getattr(d, k)
            for k in (
                "id",
                "name",
                "kind",
                "value",
                "min_purchase",
                "min_quantity",
                "start_date",
                "end_date",
                "usage_limit",
                "used_count",
                "scope",
                "active",
                "created_at",
            )
        },
        product_ids=[p.id for p in d.products],
        subscription_ids=[s.id for s in d.subscriptions],
    )


def _apply(db: Db, discount: Discount, body: DiscountIn) -> None:
    values = body.model_dump(exclude={"product_ids", "subscription_ids"})
    for key, value in values.items():
        setattr(discount, key, value)
    products = (
        list(db.scalars(select(Product).where(Product.id.in_(set(body.product_ids)))))
        if body.product_ids
        else []
    )
    subscriptions = (
        list(db.scalars(select(Subscription).where(Subscription.id.in_(set(body.subscription_ids)))))
        if body.subscription_ids
        else []
    )
    if len(products) != len(set(body.product_ids)):
        raise Invalid("One of the selected products doesn't exist.", field="product_ids")
    if len(subscriptions) != len(set(body.subscription_ids)):
        raise Invalid("One of the selected subscriptions doesn't exist.", field="subscription_ids")
    discount.products = products
    discount.subscriptions = subscriptions


@router.get("", response_model=Page[DiscountOut])
def list_discounts(db: Db, _: AdminUser, pages: Pages, q: str | None = None):
    stmt = select(Discount).options(*_LOAD).order_by(Discount.id.desc())
    if q and q.strip():
        stmt = stmt.where(Discount.name.ilike(like_pattern(q), escape="\\"))
    rows, total = paginate(db, stmt, pages)
    return Page(items=[_out(d) for d in rows], total=total, page=pages.page, page_size=pages.page_size)


@router.post("", response_model=DiscountOut, status_code=status.HTTP_201_CREATED)
def create_discount(body: DiscountIn, db: Db, _: AdminUser):
    discount = Discount(used_count=0)
    _apply(db, discount, body)
    db.add(discount)
    db.commit()
    db.refresh(discount)
    return _out(discount)


@router.patch("/{discount_id}", response_model=DiscountOut)
def update_discount(discount_id: int, body: DiscountIn, db: Db, _: AdminUser):
    discount = get_or_404(db, Discount, discount_id)
    _apply(db, discount, body)
    db.commit()
    return _out(discount)
