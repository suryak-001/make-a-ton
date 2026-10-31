"""The business that issues the invoices: its name, address, tax number and where to pay. One row; the PDF reads it."""

from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CompanyProfile(Base):
    __tablename__ = "company_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    tagline: Mapped[str | None]
    address: Mapped[str]
    email: Mapped[str]
    phone: Mapped[str | None]
    website: Mapped[str | None]
    gstin: Mapped[str | None]
    pan: Mapped[str | None]
    bank_name: Mapped[str | None]
    account_name: Mapped[str | None]
    account_number: Mapped[str | None]
    ifsc: Mapped[str | None]
    upi_id: Mapped[str | None]
    terms: Mapped[str | None]
