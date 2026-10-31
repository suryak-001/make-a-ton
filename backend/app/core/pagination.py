"""Owner: A. Server-side pagination used by every list endpoint (thousands of rows must stay fast)."""

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)) -> PageParams:
    return PageParams(page, page_size)


Pages = Annotated[PageParams, Depends(page_params)]


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


def paginate(
    db: Session, stmt: Select, params: PageParams, *, scalars: bool = True, count_from: Select | None = None
) -> tuple[list[Any], int]:
    """Runs `stmt` for one page and a COUNT over the same filters.

    scalars=True  -> rows are entities (stmt selects one model)
    scalars=False -> rows are `Row` tuples (stmt selects several columns/entities)
    count_from    -> a cheaper select with the same filters, when `stmt` carries expensive extra columns
    """
    total = (
        db.scalar(
            select(func.count()).select_from(
                (count_from if count_from is not None else stmt).order_by(None).subquery()
            )
        )
        or 0
    )
    paged = stmt.limit(params.page_size).offset(params.offset)
    rows = list(db.scalars(paged)) if scalars else list(db.execute(paged))
    return rows, total


def like_pattern(q: str) -> str:
    """`%q%` for ILIKE with the user's own % and _ escaped (use with escape="\\")."""
    escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
