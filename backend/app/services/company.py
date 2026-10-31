"""The company details printed on invoices. `MOCK_COMPANY` is sample data (the tax and bank numbers are not real):
the seed stores it, and it is also what invoices fall back to when no profile has been saved."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CompanyProfile

MOCK_COMPANY = {
    "name": "Brightloop Software Pvt Ltd",
    "tagline": "Subscriptions, billing and revenue operations",
    "address": "4th Floor, Orchid Tech Park, Infopark Phase 1\nKakkanad, Kochi, Kerala 682042, India",
    "email": "billing@brightloop.test",
    "phone": "+91 484 400 1234",
    "website": "www.brightloop.test",
    "gstin": "32AABCB1234F1Z5",
    "pan": "AABCB1234F",
    "bank_name": "Federal Bank, Kakkanad Branch",
    "account_name": "Brightloop Software Pvt Ltd",
    "account_number": "12345678901234",
    "ifsc": "FDRL0001234",
    "upi_id": "brightloop@fbl",
    "terms": (
        "Payment is due by the date shown. Please quote the invoice number with your payment. "
        "This is a computer-generated invoice and needs no signature."
    ),
}


def get_company(db: Session) -> CompanyProfile:
    """The saved profile, or the sample one when none is saved (never added to the session)."""
    return db.scalar(select(CompanyProfile).order_by(CompanyProfile.id).limit(1)) or CompanyProfile(
        **MOCK_COMPANY
    )
