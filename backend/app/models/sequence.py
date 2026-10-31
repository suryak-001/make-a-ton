from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Sequence(Base):
    """Atomic document numbering (SUB, INV-2026, ...). Use services.sequence.next_number(), never count rows."""

    __tablename__ = "sequence"

    name: Mapped[str] = mapped_column(primary_key=True)
    next: Mapped[int] = mapped_column(default=1)
