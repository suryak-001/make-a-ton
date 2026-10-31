from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import Name, OptionalText, blank_to_none
from app.schemas.subscriptions import PlanBrief


class TemplateLineIn(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(ge=1)


class TemplateIn(BaseModel):
    name: Name
    plan_id: int
    validity_days: int = Field(30, ge=1, le=365)  # how long a quote made from it stays valid once sent
    notes: OptionalText = None
    lines: list[TemplateLineIn] = Field(min_length=1)

    _blank = field_validator("notes")(blank_to_none)


class TemplateLineOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    variant_id: int | None
    variant_label: str | None
    quantity: int


class TemplateOut(BaseModel):
    id: int
    name: str
    plan: PlanBrief
    validity_days: int
    notes: str | None
    lines: list[TemplateLineOut]
    created_at: datetime
