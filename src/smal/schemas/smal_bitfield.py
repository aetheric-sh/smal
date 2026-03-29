from __future__ import annotations
from smal.schemas.utilities import IdentifierValidationMixin
from pydantic import BaseModel, field_validator, Field
from typing import ClassVar


class SMALBitField(IdentifierValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str = Field(..., description="The name of the bit field (not to be confused with bitfield).")
    bit: int = Field(..., description="The bit index within the bitfield this field is assigned to.")

    @field_validator("bit")
    def validate_bit(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Bit index must be >= 0")
        return v
