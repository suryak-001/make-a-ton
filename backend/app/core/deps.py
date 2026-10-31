"""Owner: A. Contract used by everyone: CurrentUser, require_roles(), Db.

Authorize close to the data: put `Depends(require_roles(...))` on every route that touches data.
Customers must only ever see their own records: scope queries with `user.customer.id`.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import SESSION_COOKIE, read_session
from app.db import get_db
from app.enums import Role
from app.models import User

Db = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: Db) -> User:
    user_id = read_session(request.cookies.get(SESSION_COOKIE))
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role):
    """Dependency factory: `user: User = Depends(require_roles(Role.ADMIN))`."""

    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have access to this")
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]
StaffUser = Annotated[User, Depends(require_roles(Role.ADMIN, Role.STAFF))]  # admin or staff
CustomerUser = Annotated[User, Depends(require_roles(Role.CUSTOMER))]
