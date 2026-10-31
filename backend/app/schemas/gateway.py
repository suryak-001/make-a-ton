from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.enums import PaymentMethod

Bank = Literal["HDFC", "ICICI", "SBI", "AXIS", "KOTAK"]


class CheckoutOut(BaseModel):
    """What the checkout window needs. The amount was fixed on the server; the browser only displays it."""

    order_id: str
    amount: Decimal
    currency: str
    invoice_id: int
    invoice_number: str
    merchant: str
    customer_name: str
    customer_email: str
    test_mode: bool


class CardIn(BaseModel):
    number: str = Field(min_length=12, max_length=23)
    expiry: str = Field(pattern=r"^\d{2}\s*/\s*\d{2}$")  # MM/YY
    cvv: str = Field(pattern=r"^\d{3,4}$")
    name: str | None = Field(None, max_length=80)


class ChargeIn(BaseModel):
    method: Literal["card", "upi", "netbanking"]
    card: CardIn | None = None
    otp: str | None = Field(None, max_length=8)  # the card's bank OTP step
    vpa: str | None = Field(None, max_length=80)  # UPI id
    bank: Bank | None = None
    bank_outcome: Literal["success", "failure"] | None = None  # chosen on the simulated bank page


class ChargeOut(BaseModel):
    order_id: str
    payment_id: str
    signature: str  # HMAC-SHA256 of "order_id|payment_id"; the app checks it before trusting the result
    method: PaymentMethod
    instrument: str


class VerifyIn(BaseModel):
    order_id: str = Field(max_length=32)
    payment_id: str = Field(max_length=32)
    signature: str = Field(max_length=64)
