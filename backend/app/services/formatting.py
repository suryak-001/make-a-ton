"""Money and dates written the way the screens show them, for text people read: emails, print pages, match reasons."""

from datetime import date
from decimal import Decimal


def rupees(amount: Decimal) -> str:
    """₹1,23,456.00: Indian digit grouping, as the screens show money."""
    sign = "-" if amount < 0 else ""
    whole, cents = f"{abs(amount):.2f}".split(".")
    head, tail = whole[:-3], whole[-3:]
    groups = [head[max(i - 2, 0) : i] for i in range(len(head), 0, -2)][::-1]
    return sign + "₹" + ",".join([*groups, tail] if head else [tail]) + "." + cents


def long_date(value: date) -> str:
    """31 Oct 2026."""
    return value.strftime("%d %b %Y")
