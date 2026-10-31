from pydantic import BaseModel, ConfigDict, field_validator

from app.enums import Role


class LoginIn(BaseModel):
    # Plain str on purpose: login only looks the user up. EmailStr rejects reserved domains such as
    # `.test`, which the seeded demo users use. Validate format on signup (A1), not here.
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
