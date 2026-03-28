from __future__ import annotations
from smal.schemas.utilities import IdentifierValidationMixin
from pydantic import BaseModel, field_validator
from typing import ClassVar

class SMALEnum(IdentifierValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str
    values: dict[int, str]

    @field_validator("values")
    def validate_values(cls, v: dict[int, str]) -> dict[int, str]:
        for key, val in v.items():
            if key < 0:
                raise ValueError("Enum keys must be non-negative")
            if not val.isidentifier():
                raise ValueError("Invalid enum value name: {val}")
        return v
