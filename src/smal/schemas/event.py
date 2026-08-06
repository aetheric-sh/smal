"""Module defining the Event model for representing events in a state machine.

This includes their properties, validation rules, and support for short-form representations.
"""

from __future__ import annotations  # Until Python 3.14

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from smal.schemas.utilities import IdentifierValidationMixin


class Event(IdentifierValidationMixin, BaseModel):
    """Schema defining an event in a state machine."""

    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str = Field(..., description="A unique name for the event, which serves as its identifier and may be used in transitions.")
    id: int | None = Field(
        default=None,
        description="A unique integer identifier for the event. If not provided, it may be auto-assigned based on the order of definition or other criteria.",
    )

    @classmethod
    def from_shorthand(cls, data: Any) -> Event:
        """Create an Event instance from a short-hand representation in data.

        Args:
            data (Any): The input data for the event, which can be a string (event name) or a dictionary with event properties.

        Raises:
            ValueError: If the input data is not a string or a dictionary.

        Returns:
            Event: The Event instance created from the short-hand representation.

        """
        if isinstance(data, str):
            return cls(name=data)
        if isinstance(data, dict):
            return cls.model_validate(data)
        raise ValueError(f"Invalid short-hand event representation: {data!r}. Expected a string or a dictionary.")
