from pydantic import BaseModel, ConfigDict, field_validator

from app.enums import Role
from app.schemas.common import Email, Name, Password


class LoginIn(BaseModel):
    # Plain str on purpose: login only looks the user up. Email format is validated on signup.
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize(cls, v: str) -> str:
        return v.strip().lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: Role
    customer_id: int | None = None


class SignupIn(BaseModel):
    name: Name
    email: Email
    password: Password


class ForgotPasswordIn(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordIn(BaseModel):
    token: str
    password: Password
