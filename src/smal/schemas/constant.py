from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

if TYPE_CHECKING:
    from smal.utilities.types import Identifier


class Constant(BaseModel):
    """Schema representing a constant value for a state machine."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    name: Identifier = Field(description="Constant name.")
    value: StrictInt | StrictStr = Field(description="Constant value.")
    description: str | None = Field(default=None, description="Description of the constant.")
    unit: str | None = Field(default=None, description="Unit of the constant.")
    radix: Literal["dec", "hex"] = Field(default="dec", description="Number format.")
