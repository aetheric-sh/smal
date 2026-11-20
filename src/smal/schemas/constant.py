"""Schema for a constant value defined in a SMAL (yaml) file."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

from smal.utilities.types import Identifier  # noqa: TC001 - Pydantic requires this at runtime


class Constant(BaseModel):
    """Schema representing a constant value for a state machine."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    name: Identifier = Field(description="Constant name.")
    value: StrictInt | StrictStr = Field(description="Constant value.")
    description: str | None = Field(default=None, description="Description of the constant.")
    unit: str | None = Field(default=None, description="Unit of the constant.")
    radix: Literal["dec", "hex"] = Field(default="dec", description="Number format.")
