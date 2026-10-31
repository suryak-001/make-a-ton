from sqlalchemy.orm import Session

from app.core.errors import NotFound


def get_or_404[T](db: Session, model: type[T], pk: int, label: str | None = None) -> T:
    obj = db.get(model, pk)
    if obj is None:
        raise NotFound(f"{label or model.__name__} not found")
    return obj
