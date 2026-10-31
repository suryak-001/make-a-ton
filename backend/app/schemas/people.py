from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator

from app.enums import Role
from app.schemas.common import Email, Name, OptionalText, Password, blank_to_none


class StaffCreate(BaseModel):
    name: Name
    email: Email
    password: Password  # the admin sets the initial password; the role is always STAFF


class UserListOut(BaseModel):
    id: int
    email: str
    name: str
    role: Role
    created_at: datetime
    is_active: bool = True


class CustomerIn(BaseModel):
    name: Name
    email: Email
    phone: OptionalText = None
    address: OptionalText = None

    _blank = field_validator("phone", "address")(blank_to_none)


class CustomerOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None
    address: str | None
    has_login: bool  # true when the customer can sign in to the portal
    created_at: datetime


class TimelineItem(BaseModel):
    at: datetime
    kind: Literal["subscription", "invoice", "payment"]
    title: str
    detail: str | None = None
    amount: Decimal | None = None
    link: str  # app route to open, e.g. /invoices/12
