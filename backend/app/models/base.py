from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from sqlalchemy import DateTime, Numeric
from sqlalchemy.orm import DeclarativeBase, mapped_column

# Money is always Numeric(12, 2) / Decimal — never float.
Money = Annotated[Decimal, mapped_column(Numeric(12, 2))]
Timestamp = Annotated[datetime, mapped_column(DateTime(timezone=True))]


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass
