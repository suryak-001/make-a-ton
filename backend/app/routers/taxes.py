"""Admin-managed tax rules; staff can read them while composing subscriptions.

A tax reaches a quote through the product's default taxes: `services.subscriptions._build_lines` copies
the product's active taxes onto each line and prices them with `services.pricing`. Deactivating a tax
therefore stops it applying to new or re-saved lines without touching lines already stored.
"""

from fastapi import APIRouter, status
from sqlalchemy import func, select

from app.core.deps import AdminUser, Db, StaffUser
from app.core.errors import Conflict, Invalid
from app.core.lookup import get_or_404
from app.core.pagination import Page, Pages, like_pattern, paginate
from app.models import Tax
from app.models.subscriptions import subscription_line_taxes
from app.schemas.money import TaxIn, TaxOut

router = APIRouter(prefix="/api/taxes", tags=["taxes"])


def _check_name_is_free(db: Db, name: str, own_id: int | None = None) -> None:
    stmt = select(Tax.id).where(func.lower(Tax.name) == name.lower())
    if own_id is not None:
        stmt = stmt.where(Tax.id != own_id)
    if db.scalar(stmt) is not None:
        raise Invalid("A tax with this name already exists.", field="name")


@router.get("", response_model=Page[TaxOut])
def list_taxes(db: Db, _: StaffUser, pages: Pages, q: str | None = None, active: bool | None = None):
    stmt = select(Tax).order_by(Tax.name, Tax.id)
    if q and q.strip():
        stmt = stmt.where(Tax.name.ilike(like_pattern(q), escape="\\"))
    if active is not None:
        stmt = stmt.where(Tax.active == active)
    rows, total = paginate(db, stmt, pages)
    return Page(items=rows, total=total, page=pages.page, page_size=pages.page_size)


@router.post("", response_model=TaxOut, status_code=status.HTTP_201_CREATED)
def create_tax(body: TaxIn, db: Db, _: AdminUser):
    _check_name_is_free(db, body.name)
    tax = Tax(**body.model_dump())
    db.add(tax)
    db.commit()
    return tax


@router.get("/{tax_id}", response_model=TaxOut)
def get_tax(tax_id: int, db: Db, _: StaffUser):
    return get_or_404(db, Tax, tax_id)


@router.put("/{tax_id}", response_model=TaxOut)
def update_tax(tax_id: int, body: TaxIn, db: Db, _: AdminUser):
    tax = get_or_404(db, Tax, tax_id)
    _check_name_is_free(db, body.name, own_id=tax.id)
    for key, value in body.model_dump().items():
        setattr(tax, key, value)
    db.commit()
    return tax


@router.delete("/{tax_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tax(tax_id: int, db: Db, _: AdminUser):
    tax = get_or_404(db, Tax, tax_id)
    in_use = db.scalar(
        select(func.count())
        .select_from(subscription_line_taxes)
        .where(subscription_line_taxes.c.tax_id == tax.id)
    )
    if in_use:
        raise Conflict("This tax is used by subscription lines. Mark it inactive instead.")
    db.delete(tax)  # product default-tax links go with it (ON DELETE CASCADE)
    db.commit()
