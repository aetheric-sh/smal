from __future__ import annotations
from smal.schemas.utilities import IdentifierValidationMixin
from pydantic import BaseModel, field_validator
from typing import ClassVar

class SMALBitField(IdentifierValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str
    bit: int

    @field_validator("bit")
    def validate_bit(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Bit index must be >= 0")
        return v