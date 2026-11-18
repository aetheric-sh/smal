"""Module defining the Error model for representing errors in a state machine.

This includes their properties, validation rules, and support for short form definitions.
"""

from __future__ import annotations  # Until Python 3.14

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

if TYPE_CHECKING:
    from smal.utilities.types import Identifier


class Error(BaseModel):
    """Schema representing an error in a state machine."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")  # Not frozen: ids are auto-assigned by Machine.enforce_monotonic_ids

    name: Identifier = Field(description="Error name.")
    id: StrictInt | None = Field(
        default=None,
        description="A unique integer identifier for the error. If not provided, it may be auto-assigned based on the order of definition or other criteria.",
    )
    description: StrictStr | None = Field(default=None, description="Description of the error, if any.")

    @model_validator(mode="before")
    @classmethod
    def _from_shorthand(cls, data: Any) -> Any:
        return {"name": data} if isinstance(data, str) else data
