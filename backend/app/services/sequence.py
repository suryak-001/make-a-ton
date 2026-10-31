from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Sequence


def next_number(db: Session, name: str, prefix: str, pad: int = 5) -> str:
    """Atomically reserves the next number in a named sequence (safe under concurrency).

    next_number(db, "SUB", "SUB-")            -> "SUB-00001"
    next_number(db, "INV-2026", "INV-2026-")  -> "INV-2026-00001"
    Runs in the caller's transaction, so a rollback gives the number back.
    """
    stmt = insert(Sequence).values(name=name, next=2)
    stmt = stmt.on_conflict_do_update(index_elements=[Sequence.name], set_={"next": Sequence.next + 1})
    value = db.execute(stmt.returning(Sequence.next)).scalar_one()
    return f"{prefix}{value - 1:0{pad}d}"
