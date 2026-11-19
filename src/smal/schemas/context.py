from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from smal.utilities.types import Identifier  # noqa: TC001 - Pydantic requires this at runtime


class ContextVar(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    name: Identifier = Field(description="Name of the context variable.")
    type: Identifier = Field(description="Datatype of the context variable.")
    default_value: JsonValue = Field(description="Default value.")
    value_constraints: list[JsonValue] | None = Field(default=None, description="Value constraints.")
