from pydantic import BaseModel


class ActiveIn(BaseModel):
    """Body of the quick Active / Inactive switch on a list row."""

    active: bool
