import enum


class Role(enum.StrEnum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    CUSTOMER = "CUSTOMER"


class ProductType(enum.StrEnum):
    SERVICE = "SERVICE"
    GOODS = "GOODS"


class BillingPeriod(enum.StrEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class SubscriptionStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    QUOTATION = "QUOTATION"
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class AmountKind(enum.StrEnum):
    PERCENT = "PERCENT"
    FIXED = "FIXED"


class DiscountScope(enum.StrEnum):
    PRODUCT = "PRODUCT"
    SUBSCRIPTION = "SUBSCRIPTION"


class InvoiceStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class PaymentMethod(enum.StrEnum):
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    CARD = "CARD"
    UPI = "UPI"
    CHEQUE = "CHEQUE"
    OTHER = "OTHER"


class GatewayOrderStatus(enum.StrEnum):
    CREATED = "CREATED"  # waiting for the customer to pay; a failed attempt leaves it here so they can retry
    PAID = "PAID"
    REFUND_DUE = "REFUND_DUE"  # the gateway took the money but the invoice had been settled meanwhile
