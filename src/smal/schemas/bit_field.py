"""Module defining the BitField model for representing individual fields within a bitfield."""

from __future__ import annotations  # Until Python 3.14

from typing import ClassVar

from pydantic import BaseModel, Field, field_validator

from smal.schemas.utilities import IdentifierValidationMixin


class BitField(IdentifierValidationMixin, BaseModel):
    """Schema defining an individual field within a bitfield. Not to be confused with the bitfield itself."""

    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str = Field(..., description="The name of the bit field (not to be confused with bitfield).")
    bit: int = Field(..., description="The bit index within the bitfield this field is assigned to.")

    @field_validator("bit")
    @classmethod
    def validate_bit(cls, v: int) -> int:
        """Validate a bit within the bitfield.

        Args:
            v (int): The bit index to validate, which must be a non-negative integer.

        Raises:
            ValueError: If the bit index is negative, which is invalid for a bitfield.

        Returns:
            int: The validated bit index, guaranteed to be non-negative.

        """
        if v < 0:
            raise ValueError("Bit index must be >= 0")
        return v
