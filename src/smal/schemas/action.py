"""Module defining the schema for the Action object in a SMAL file."""

from __future__ import annotations  # Until Python 3.14

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr, model_validator

from smal.utilities import expressions as SMALExpressions

if TYPE_CHECKING:
    from smal.utilities.types import Identifier


class Action(BaseModel):
    """Schema representing an Action (executable step) within a state machine."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    name: Identifier = Field(description="Action name.")
    sets: dict[Identifier, StrictBool | StrictInt | StrictStr | StrictFloat] = Field(
        default_factory=dict,
        description=(
            "Context variable assignments this action performs, applied in order. Values are literals or expressions over context variables, "
            "constants and enum members, e.g. {foo: bar, attempts: 'attempts + 1'}. Used for path analysis."
        ),
    )
    description: StrictStr | None = Field(default=None, description="Description of the action.")

    @model_validator(mode="before")
    @classmethod
    def _from_shorthand(cls, data: Any) -> Any:
        return {"name": data} if isinstance(data, str) else data

    @model_validator(mode="after")
    def _check_set_expressions(self) -> Action:
        for value in self.sets.values():
            if isinstance(value, str):
                SMALExpressions.parse(value)  # Raises ValueError on invalid syntax
        return self
