"""Module defining the Event model for representing events in a state machine.

This includes their properties, validation rules, and support for short-form representations.
"""

from __future__ import annotations  # Until Python 3.14

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

if TYPE_CHECKING:
    from smal.utilities.types import Identifier


class Event(BaseModel):
    """Schema defining an event in a state machine."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    name: Identifier = Field(description="The name of the event.")
    id: StrictInt | None = Field(
        default=None,
        description="A unique integer identifier for the event. If not provided, it may be auto-assigned based on the order of definition or other criteria.",
    )

    @model_validator(mode="before")
    @classmethod
    def _from_shorthand(cls, data: Any) -> Any:
        return {"name": data} if isinstance(data, str) else data
