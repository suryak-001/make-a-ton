"""Admin-managed tax rules; staff can read them while composing subscriptions."""

from fastapi import APIRouter, status
from sqlalchemy import select

from app.core.deps import AdminUser, Db, StaffUser
from app.core.lookup import get_or_404
from app.core.pagination import Page, Pages, like_pattern, paginate
from app.models import Tax
from app.schemas.money import TaxIn, TaxOut

router = APIRouter(prefix="/api/taxes", tags=["taxes"])


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
    tax = Tax(**body.model_dump())
    db.add(tax)
    db.commit()
    return tax


@router.patch("/{tax_id}", response_model=TaxOut)
def update_tax(tax_id: int, body: TaxIn, db: Db, _: AdminUser):
    tax = get_or_404(db, Tax, tax_id)
    for key, value in body.model_dump().items():
        setattr(tax, key, value)
    db.commit()
    return tax
