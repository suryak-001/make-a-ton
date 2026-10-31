from decimal import Decimal
from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, Field, StringConstraints
from pydantic_core import PydanticCustomError

from app.core.security import password_problems


def _normalize_email(value: str) -> str:
    try:
        # test_environment=True lets reserved domains like `.test` through (the demo users use them).
        return validate_email(
            value.strip(), check_deliverability=False, test_environment=True
        ).normalized.lower()
    except EmailNotValidError as e:
        raise PydanticCustomError("email", "{reason}", {"reason": str(e)}) from e


def _check_password(value: str) -> str:
    problems = password_problems(value)
    if problems:
        raise PydanticCustomError("password_policy", "{problems}", {"problems": " ".join(problems)})
    return value


Email = Annotated[str, AfterValidator(_normalize_email)]
Password = Annotated[str, AfterValidator(_check_password)]  # the brief's password policy
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
OptionalText = Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=500)]


def blank_to_none(value: str | None) -> str | None:
    return value or None


# Non-negative money with at most 2 decimal places; accepts 12, "12.5" or 12.50 in JSON.
MoneyIn = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
