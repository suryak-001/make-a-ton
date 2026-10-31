"""The demo payment gateway's own endpoint: what the checkout window talks to when the customer pays.

In production this is the real gateway's servers, not this app. See services/gateway.py.
"""

from fastapi import APIRouter

from app.core.deps import CustomerUser, Db
from app.schemas.gateway import ChargeIn, ChargeOut
from app.services import gateway

router = APIRouter(prefix="/api/demo-gateway", tags=["demo-gateway"])


@router.post("/orders/{order_id}/charge", response_model=ChargeOut)
def charge(order_id: str, body: ChargeIn, db: Db, user: CustomerUser):
    """Approved: the payment id and its signature. Declined: 402 with the reason, and the order stays open."""
    try:
        result = gateway.charge(db, user, order_id, body)
    except gateway.PaymentDeclined:
        db.commit()  # keep the attempt count and the reason
        raise
    db.commit()
    return result
