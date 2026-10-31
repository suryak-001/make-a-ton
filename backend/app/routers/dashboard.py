"""The first screen for each role: admin proof and setup, the staff work queue, the customer's account at a glance."""

from fastapi import APIRouter

from app.core.deps import AdminUser, CustomerUser, Db, StaffUser
from app.core.errors import NotFound
from app.models import Invoice
from app.services import dashboard as svc

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/aging", response_model=list[svc.AgingBucket])
def aging(db: Db, _: AdminUser):
    return svc.aging(db)


@router.get("/proof", response_model=svc.Proof)
def proof(db: Db, _: AdminUser):
    return svc.proof(db)


@router.get("/setup", response_model=list[svc.SetupStep])
def setup(db: Db, _: AdminUser):
    return svc.setup_steps(db)


@router.get("/queue", response_model=svc.WorkQueue)
def queue(db: Db, _: StaffUser):
    return svc.work_queue(db)


@router.post("/remind/{invoice_id}")
def remind(invoice_id: int, db: Db, user: StaffUser):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise NotFound("Invoice not found.")
    stage = svc.remind(db, invoice, user.id)
    db.commit()
    return {"stage": stage}


@router.get("/portal", response_model=svc.PortalHome)
def portal(db: Db, user: CustomerUser):
    if user.customer is None:
        raise NotFound("No customer account is linked to this login.")
    return svc.portal_home(db, user.customer)
