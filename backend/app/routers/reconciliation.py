"""Bank reconciliation: upload a statement, review the suggested matches, record the approved payments."""

from fastapi import APIRouter
from fastapi.responses import Response

from app.core.deps import Db, StaffUser
from app.schemas.reconciliation import ApplyIn, ApplyOut, PreviewOut, StatementIn
from app.services import reconciliation as svc

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])


@router.post("/preview", response_model=PreviewOut)
def preview(body: StatementIn, db: Db, _: StaffUser):
    """Reads the statement and suggests an invoice for each credit. Records nothing."""
    return svc.preview(db, body.csv)


@router.post("/apply", response_model=ApplyOut)
def apply(body: ApplyIn, db: Db, user: StaffUser):
    """Records the approved lines as payments. A line that was recorded before is reported, never paid twice."""
    result = svc.apply(db, body.items, user)
    db.commit()
    return result


@router.get("/sample.csv")
def sample(db: Db, _: StaffUser):
    """A statement built from today's open invoices, to try reconciliation without a real bank file."""
    return Response(
        svc.sample_statement(db),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="sample-bank-statement.csv"'},
    )
