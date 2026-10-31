"""Owner: A. login / logout / me are real; signup (A1) and password reset (A2) are next."""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.config import settings
from app.core.deps import CurrentUser, Db
from app.core.security import SESSION_COOKIE, hash_password, sign_session, verify_password
from app.models import User
from app.schemas import LoginIn, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

_DUMMY_HASH = hash_password("dummy-password-for-timing")  # so unknown emails cost the same as wrong passwords


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        customer_id=user.customer.id if user.customer else None,
    )


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Db):
    user = db.scalar(select(User).where(User.email == body.email))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    response.set_cookie(
        SESSION_COOKIE,
        sign_session(user.id),
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user_out(user)


# TODO(A1): POST /signup — unique email, core.security.password_problems(), create User(CUSTOMER) + Customer, sign in.
# TODO(A2): POST /forgot-password and /reset-password — hashed single-use PasswordResetToken (1h), services.mail.send_mail().
