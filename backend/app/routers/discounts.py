"""Admin-managed automatic discount rules."""

from fastapi import APIRouter, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import AdminUser, Db
from app.core.errors import Conflict, Invalid, NotFound
from app.core.lookup import get_or_404
from app.core.pagination import Page, Pages, like_pattern, paginate
from app.enums import DiscountScope
from app.models import Discount, DiscountUsage, Product, Subscription
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
    products = _find_all(db, Product, body.product_ids, "product_ids", "products")
    subscriptions = _find_all(db, Subscription, body.subscription_ids, "subscription_ids", "subscriptions")
    _require_target(body, products, subscriptions)
    for key, value in body.model_dump(exclude={"product_ids", "subscription_ids"}).items():
        setattr(discount, key, value)
    discount.products = products
    discount.subscriptions = subscriptions


def _find_all[T](db: Db, model: type[T], ids: list[int], field: str, label: str) -> list[T]:
    wanted = set(ids)
    found = list(db.scalars(select(model).where(model.id.in_(wanted)))) if wanted else []
    if len(found) != len(wanted):
        raise Invalid(f"One of the selected {label} doesn't exist.", field=field)
    return found


def _require_target(body: DiscountIn, products: list[Product], subscriptions: list[Subscription]) -> None:
    if body.scope == DiscountScope.PRODUCT and not products:
        raise Invalid("Select at least one product for a product discount.", field="product_ids")
    if body.scope == DiscountScope.SUBSCRIPTION and not subscriptions:
        raise Invalid(
            "Select at least one subscription for a subscription discount.", field="subscription_ids"
        )


@router.get("", response_model=Page[DiscountOut])
def list_discounts(db: Db, _: AdminUser, pages: Pages, q: str | None = None, active: bool | None = None):
    stmt = select(Discount).options(*_LOAD).order_by(Discount.id.desc())
    if active is not None:
        stmt = stmt.where(Discount.active == active)
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


def _load(db: Db, discount_id: int) -> Discount:
    discount = db.scalar(select(Discount).where(Discount.id == discount_id).options(*_LOAD))
    if discount is None:
        raise NotFound("Discount not found")
    return discount


@router.get("/{discount_id}", response_model=DiscountOut)
def get_discount(discount_id: int, db: Db, _: AdminUser):
    return _out(_load(db, discount_id))


@router.put("/{discount_id}", response_model=DiscountOut)
def update_discount(discount_id: int, body: DiscountIn, db: Db, _: AdminUser):
    discount = _load(db, discount_id)
    if body.usage_limit is not None and body.usage_limit < discount.used_count:
        raise Invalid(f"It has already been used {discount.used_count} times.", field="usage_limit")
    _apply(db, discount, body)
    db.commit()
    return _out(discount)


@router.delete("/{discount_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discount(discount_id: int, db: Db, _: AdminUser):
    discount = get_or_404(db, Discount, discount_id)
    used = db.scalar(
        select(func.count()).select_from(DiscountUsage).where(DiscountUsage.discount_id == discount.id)
    )
    if used:
        raise Conflict("This discount already appears on invoices. Mark it inactive instead.")
    db.delete(discount)
    db.commit()
