import calendar
from datetime import date, timedelta

from app.enums import BillingPeriod


def add_period(d: date, period: BillingPeriod, count: int = 1) -> date:
    """Next period start. Month/year math clamps to the last day (Jan 31 + 1 month = Feb 28/29)."""
    match period:
        case BillingPeriod.DAILY:
            return d + timedelta(days=count)
        case BillingPeriod.WEEKLY:
            return d + timedelta(weeks=count)
        case BillingPeriod.MONTHLY | BillingPeriod.YEARLY:
            months = count if period == BillingPeriod.MONTHLY else 12 * count
            index = d.year * 12 + (d.month - 1) + months
            year, month = divmod(index, 12)
            month += 1
            return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))
