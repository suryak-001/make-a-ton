# Import every model module so Base.metadata (Alembic, create_all) sees all tables.
from app.models.base import Base
from app.models.billing import DiscountUsage, GatewayOrder, Invoice, InvoiceLine, InvoiceReminder, Payment
from app.models.catalog import Plan, Product, ProductVariant, QuotationTemplate, QuotationTemplateLine
from app.models.company import CompanyProfile
from app.models.identity import Customer, PasswordResetToken, User
from app.models.rules import Discount, Tax
from app.models.sequence import Sequence
from app.models.subscriptions import Subscription, SubscriptionEvent, SubscriptionLine

__all__ = [
    "Base",
    "CompanyProfile",
    "Customer",
    "Discount",
    "DiscountUsage",
    "GatewayOrder",
    "Invoice",
    "InvoiceLine",
    "InvoiceReminder",
    "PasswordResetToken",
    "Payment",
    "Plan",
    "Product",
    "ProductVariant",
    "QuotationTemplate",
    "QuotationTemplateLine",
    "Sequence",
    "Subscription",
    "SubscriptionEvent",
    "SubscriptionLine",
    "Tax",
    "User",
]
