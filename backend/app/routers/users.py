"""Owner: A — admin-only user management. Only the admin can add a member of staff."""

from fastapi import APIRouter, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import AdminUser, Db
from app.core.errors import Conflict
from app.core.pagination import Page, Pages, like_pattern, paginate
from app.core.security import hash_password
from app.enums import Role
from app.models import User
from app.schemas.people import StaffCreate, UserListOut

router = APIRouter(prefix="/api/users", tags=["users"])


def _out(u: User) -> UserListOut:
    return UserListOut(id=u.id, email=u.email, name=u.name, role=u.role, created_at=u.created_at)


@router.get("", response_model=Page[UserListOut])
def list_users(db: Db, _: AdminUser, pages: Pages, q: str | None = None, role: Role | None = None):
    stmt = select(User).order_by(User.role, User.name, User.id)
    if role:
        stmt = stmt.where(User.role == role)
    if q and q.strip():
        like = like_pattern(q)
        stmt = stmt.where(or_(User.name.ilike(like, escape="\\"), User.email.ilike(like, escape="\\")))
    rows, total = paginate(db, stmt, pages)
    return Page(items=[_out(u) for u in rows], total=total, page=pages.page, page_size=pages.page_size)


@router.post("", response_model=UserListOut, status_code=status.HTTP_201_CREATED)
def add_staff(body: StaffCreate, db: Db, _: AdminUser):
    if db.scalar(select(User.id).where(User.email == body.email)):
        raise Conflict("An account with this email already exists.", field="email")
    user = User(email=body.email, name=body.name, role=Role.STAFF, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict("An account with this email already exists.", field="email") from None
    return _out(user)
