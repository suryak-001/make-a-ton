"""Owner: B — users, password reset tokens, customers."""

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import Role
from app.models.base import Base, Timestamp, utcnow


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)  # stored lower-cased
    password_hash: Mapped[str]
    name: Mapped[str]
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"), default=Role.CUSTOMER)
    created_at: Mapped[Timestamp] = mapped_column(default=utcnow)
    # Set when an admin chose the first password: the person must replace it on first sign-in.
    # False once an admin has switched the account off: it can no longer sign in or use a session.
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    must_change_password: Mapped[bool] = mapped_column(default=False, server_default="false")

    customer: Mapped["Customer | None"] = relationship(back_populates="user")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_token"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)  # sha256 of the emailed token
    expires_at: Mapped[Timestamp]
    used_at: Mapped[Timestamp | None]
    created_at: Mapped[Timestamp] = mapped_column(default=utcnow)


class Customer(Base):
    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True)
    email: Mapped[str] = mapped_column(index=True)
    phone: Mapped[str | None]
    address: Mapped[str | None]
    # Set when the customer has a portal login.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"), unique=True)
    created_at: Mapped[Timestamp] = mapped_column(default=utcnow)

    user: Mapped[User | None] = relationship(back_populates="customer")
