"""Module defining the Error model for representing errors in a state machine.

This includes their properties, validation rules, and support for short form definitions.
"""

from __future__ import annotations  # Until Python 3.14

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from smal.schemas.utilities import IdentifierValidationMixin


class Error(IdentifierValidationMixin, BaseModel):
    """Schema defining an error in a state machine."""

    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str = Field(..., description="A unique name for the error, which serves as its identifier and may be used in transitions or other contexts.")
    id: int | None = Field(
        default=None,
        description="A unique integer identifier for the error. If not provided, it may be auto-assigned based on the order of definition or other criteria.",
    )
    description: str | None = Field(default=None, description="Description of the error, if any.")

    @classmethod
    def from_shorthand(cls, data: Any) -> Error:
        """Create a Error instance from a short-hand representation in data.

        Args:
            data (Any): The input data for the error, which can be a string (error name) or a dictionary with error properties.

        Raises:
            ValueError: If the input data is not a string or a dictionary.

        Returns:
            Error: The Error instance created from the short-hand representation.

        """
        if isinstance(data, str):
            return cls(name=data)
        if isinstance(data, dict):
            return cls.model_validate(data)
        raise ValueError(f"Invalid short-hand error representation: {data!r}. Expected a string or a dictionary.")
