from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, ConfigDict, Field, JsonValue

if TYPE_CHECKING:
    from smal.utilities.types import Identifier


class ContextVar(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    name: Identifier = Field(description="Name of the context variable.")
    type: Identifier = Field(description="Datatype of the context variable.")
    default_value: JsonValue = Field(description="Default value.")
    value_constraints: list[JsonValue] | None = Field(default=None, description="Value constraints.")
