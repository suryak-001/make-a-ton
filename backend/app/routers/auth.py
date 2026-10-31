"""Owner: B — sign up, sign in/out and password reset (B1)."""

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.core.deps import CurrentUser, Db
from app.core.errors import Conflict, Invalid
from app.core.security import (
    SESSION_COOKIE,
    hash_password,
    hash_reset_token,
    new_reset_token,
    set_session_cookie,
    verify_password,
)
from app.enums import Role
from app.models import Customer, PasswordResetToken, User
from app.models.base import utcnow
from app.schemas.auth import ChangePasswordIn, ForgotPasswordIn, LoginIn, ResetPasswordIn, SignupIn, UserOut
from app.services.mail import send_mail

router = APIRouter(prefix="/api/auth", tags=["auth"])

RESET_TOKEN_TTL = timedelta(hours=1)
_DUMMY_HASH = hash_password("dummy-password-for-timing")  # so unknown emails cost the same as wrong passwords


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        customer_id=user.customer.id if user.customer else None,
        must_change_password=user.must_change_password,
    )


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupIn, response: Response, db: Db):
    """Self-service sign up. Always creates a CUSTOMER; staff are added by an admin (POST /api/users)."""
    if db.scalar(select(User.id).where(User.email == body.email)):
        raise Conflict("An account with this email already exists.", field="email")

    user = User(
        email=body.email, name=body.name, role=Role.CUSTOMER, password_hash=hash_password(body.password)
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:  # two signups racing past the check above; the unique index decides
        db.rollback()
        raise Conflict("An account with this email already exists.", field="email") from None

    # A sales rep may already have created this customer: attach the login to it instead of duplicating.
    customer = db.scalar(
        select(Customer).where(Customer.email == body.email, Customer.user_id.is_(None)).order_by(Customer.id)
    )
    if customer:
        customer.user_id = user.id
    else:
        db.add(Customer(name=body.name, email=body.email, user_id=user.id))
    db.commit()

    set_session_cookie(response, user.id)
    return user_out(user)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Db):
    user = db.scalar(select(User).where(User.email == body.email))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    set_session_cookie(response, user.id)
    return user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user_out(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: ChangePasswordIn, user: CurrentUser, db: Db):
    """The signed-in person chooses a new password (required once for staff an admin added)."""
    if not verify_password(body.current_password, user.password_hash):
        raise Invalid("The current password is not right.", field="current_password")
    if verify_password(body.new_password, user.password_hash):
        raise Invalid("Choose a password you haven't used just now.", field="new_password")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    db.commit()


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(body: ForgotPasswordIn, db: Db):
    """Emails a reset link to the registered address. The response is identical whether or not the
    account exists, so this can't be used to find out who has an account."""
    user = db.scalar(select(User).where(User.email == body.email))
    if user:
        now = utcnow()
        # Only the newest link works.
        db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
            .values(used_at=now)
        )
        token, token_hash = new_reset_token()
        db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=now + RESET_TOKEN_TTL))
        db.commit()
        link = f"{settings.frontend_url}/reset-password?token={token}"
        send_mail(
            user.email,
            "Reset your Brightloop password",
            f"Hi {user.name},\n\nUse this link to choose a new password (valid for 1 hour):\n{link}\n\n"
            "If you didn't ask for this, you can ignore this email.",
        )
    return {"detail": "If an account exists for that email, a reset link is on its way."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(body: ResetPasswordIn, db: Db):
    now = utcnow()
    record = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_reset_token(body.token))
        .with_for_update()
    )
    if record is None or record.used_at is not None or record.expires_at <= now:
        raise Invalid("This reset link is invalid or has expired. Request a new one.")
    user = db.get(User, record.user_id)
    user.password_hash = hash_password(body.password)
    user.must_change_password = False
    record.used_at = now  # single use
    db.commit()
