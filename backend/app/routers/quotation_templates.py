"""Owner: B — quotation templates (admin + staff): a plan plus product lines and a validity in days."""

from datetime import date

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import Db, StaffUser
from app.core.errors import Invalid
from app.core.lookup import get_or_404
from app.core.pagination import Page, Pages, like_pattern, paginate
from app.models import Plan, Product, QuotationTemplate, QuotationTemplateLine
from app.schemas.subscriptions import FromTemplateIn, LineIn, SubscriptionDetail, SubscriptionIn
from app.schemas.templates import TemplateIn, TemplateLineOut, TemplateOut
from app.services.subscription_views import load_detail, staff_detail
from app.services.subscriptions import create_subscription

router = APIRouter(prefix="/api/quotation-templates", tags=["quotation-templates"])

_LOAD = (
    selectinload(QuotationTemplate.plan),
    selectinload(QuotationTemplate.lines).selectinload(QuotationTemplateLine.product),
    selectinload(QuotationTemplate.lines).selectinload(QuotationTemplateLine.variant),
)


def _out(t: QuotationTemplate) -> TemplateOut:
    return TemplateOut(
        id=t.id,
        name=t.name,
        plan={"id": t.plan.id, "name": t.plan.name, "billing_period": t.plan.billing_period},
        validity_days=t.validity_days,
        notes=t.notes,
        created_at=t.created_at,
        lines=[
            TemplateLineOut(
                id=line.id,
                product_id=line.product_id,
                product_name=line.product.name,
                variant_id=line.variant_id,
                variant_label=f"{line.variant.attribute}: {line.variant.value}" if line.variant else None,
                quantity=line.quantity,
            )
            for line in t.lines
        ],
    )


def _load(db: Session, template_id: int) -> QuotationTemplate:
    t = db.scalar(select(QuotationTemplate).where(QuotationTemplate.id == template_id).options(*_LOAD))
    return t if t else get_or_404(db, QuotationTemplate, template_id, "Template")


def _apply(db: Session, template: QuotationTemplate, body: TemplateIn) -> None:
    plan = db.get(Plan, body.plan_id)
    if plan is None:
        raise Invalid("This plan doesn't exist.", field="plan_id")
    products = {
        p.id: p
        for p in db.scalars(
            select(Product)
            .where(Product.id.in_({li.product_id for li in body.lines}))
            .options(selectinload(Product.variants))
        )
    }
    lines = []
    for i, li in enumerate(body.lines):
        product = products.get(li.product_id)
        if product is None:
            raise Invalid("This product doesn't exist.", field=f"lines.{i}.product_id")
        if li.variant_id is not None and all(v.id != li.variant_id for v in product.variants):
            raise Invalid("That variant doesn't belong to this product.", field=f"lines.{i}.variant_id")
        if li.quantity < plan.min_quantity:
            raise Invalid(
                f"Quantity must be at least {plan.min_quantity} on this plan.", field=f"lines.{i}.quantity"
            )
        lines.append(
            QuotationTemplateLine(product_id=li.product_id, variant_id=li.variant_id, quantity=li.quantity)
        )

    template.name, template.plan_id = body.name, body.plan_id
    template.validity_days, template.notes = body.validity_days, body.notes
    template.lines.clear()
    template.lines.extend(lines)


@router.get("", response_model=Page[TemplateOut])
def list_templates(db: Db, _: StaffUser, pages: Pages, q: str | None = None):
    stmt = select(QuotationTemplate).options(*_LOAD).order_by(QuotationTemplate.name, QuotationTemplate.id)
    if q and q.strip():
        stmt = stmt.where(QuotationTemplate.name.ilike(like_pattern(q), escape="\\"))
    rows, total = paginate(db, stmt, pages)
    return Page(items=[_out(t) for t in rows], total=total, page=pages.page, page_size=pages.page_size)


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(body: TemplateIn, db: Db, _: StaffUser):
    template = QuotationTemplate()
    _apply(db, template, body)
    db.add(template)
    db.commit()
    return _out(_load(db, template.id))


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(template_id: int, db: Db, _: StaffUser):
    return _out(_load(db, template_id))


@router.put("/{template_id}", response_model=TemplateOut)
def update_template(template_id: int, body: TemplateIn, db: Db, _: StaffUser):
    template = _load(db, template_id)
    _apply(db, template, body)
    db.commit()
    return _out(_load(db, template_id))


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: Db, _: StaffUser):
    db.delete(get_or_404(db, QuotationTemplate, template_id, "Template"))
    db.commit()


@router.post(
    "/{template_id}/create-subscription",
    response_model=SubscriptionDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_subscription_from_template(template_id: int, body: FromTemplateIn, db: Db, user: StaffUser):
    """Starts a DRAFT subscription from the template's plan and lines. The quote's validity is counted
    from the day it is sent, using the template's validity_days."""
    t = _load(db, template_id)
    data = SubscriptionIn(
        customer_id=body.customer_id,
        plan_id=t.plan_id,
        start_date=body.start_date or date.today(),
        expiry_date=body.expiry_date,
        payment_term_days=body.payment_term_days,
        validity_days=t.validity_days,
        lines=[
            LineIn(product_id=ln.product_id, variant_id=ln.variant_id, quantity=ln.quantity) for ln in t.lines
        ],
    )
    sub = create_subscription(db, data, user)
    db.commit()
    return staff_detail(load_detail(db, sub.id))
