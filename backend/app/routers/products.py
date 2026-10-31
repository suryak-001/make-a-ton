"""Owner: B — products and their variants. Staff can read; only the admin can change them."""

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.deps import AdminUser, Db, StaffUser
from app.core.errors import Conflict, Invalid
from app.core.lookup import get_or_404
from app.core.pagination import Page, Pages, like_pattern, paginate
from app.models import Product, ProductVariant, Tax
from app.schemas.catalog import ProductIn, ProductOut

router = APIRouter(prefix="/api/products", tags=["products"])

_LOAD = (selectinload(Product.variants), selectinload(Product.default_taxes))


def _apply(db: Db, product: Product, body: ProductIn) -> None:
    for field in ("name", "type", "sales_price", "cost_price", "notes", "active", "is_addon"):
        setattr(product, field, getattr(body, field))

    ids = set(body.default_tax_ids)
    taxes = list(db.scalars(select(Tax).where(Tax.id.in_(ids)))) if ids else []
    if len(taxes) != len(ids):
        raise Invalid("One of the selected taxes doesn't exist.", field="default_tax_ids")
    product.default_taxes = taxes

    existing = {v.id: v for v in product.variants}
    keep: set[int] = set()
    for vin in body.variants:
        if vin.id is None:
            product.variants.append(
                ProductVariant(attribute=vin.attribute, value=vin.value, extra_price=vin.extra_price)
            )
            continue
        variant = existing.get(vin.id)
        if variant is None:
            raise Invalid("A variant doesn't belong to this product.", field="variants")
        variant.attribute, variant.value, variant.extra_price = vin.attribute, vin.value, vin.extra_price
        keep.add(vin.id)
    for variant_id, variant in existing.items():
        if variant_id not in keep:
            product.variants.remove(variant)  # delete-orphan removes the row


def _commit(db: Db, message: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict(message) from None


@router.get("", response_model=Page[ProductOut])
def list_products(db: Db, _: StaffUser, pages: Pages, q: str | None = None, active: bool | None = None):
    stmt = select(Product).options(*_LOAD).order_by(Product.name, Product.id)
    if active is not None:
        stmt = stmt.where(Product.active == active)
    if q and q.strip():
        stmt = stmt.where(Product.name.ilike(like_pattern(q), escape="\\"))
    rows, total = paginate(db, stmt, pages)
    return Page(items=rows, total=total, page=pages.page, page_size=pages.page_size)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(body: ProductIn, db: Db, _: AdminUser):
    product = Product()
    _apply(db, product, body)
    db.add(product)
    _commit(db, "Two variants have the same attribute and value.")
    return product


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Db, _: StaffUser):
    return get_or_404(db, Product, product_id)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, body: ProductIn, db: Db, _: AdminUser):
    product = get_or_404(db, Product, product_id)
    _apply(db, product, body)
    _commit(db, "A variant that's used by a subscription or template can't be removed. Edit it instead.")
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Db, _: AdminUser):
    product = get_or_404(db, Product, product_id)
    db.delete(product)
    _commit(db, "This product is used by subscriptions or templates. Mark it inactive instead.")
