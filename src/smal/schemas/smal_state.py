from enum import Enum
from functools import cached_property
from typing import ClassVar

from pydantic import BaseModel, Field

from smal.schemas.utilities import IdentifierValidationMixin


class SMALStateType(str, Enum):
    NORMAL = "normal"
    INITIAL = "initial"
    FINAL = "final"
    SUPERSTATE = "superstate"
    SUBSTATE = "substate"
    DECISION = "decision"
    ERROR = "error"

    @cached_property
    def graphviz_shape(self) -> str:
        return {
            self.NORMAL: "ellipse",
            self.INITIAL: "circle",
            self.FINAL: "doublecircle",
            self.SUPERSTATE: "box",
            self.SUBSTATE: "rectangle",
            self.DECISION: "diamond",
            self.ERROR: "octagon",
        }[self]


class SMALState(IdentifierValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str = Field(..., description="A unique name for the state, which serves as its identifier and may be used in transitions.")
    id: int | None = Field(
        default=None,
        description="A unique integer identifier for the state. If not provided, it may be auto-assigned based on the order of definition or other criteria.",
    )
    description: str | None = Field(default=None, description="A human-readable description of the state.")
    type: SMALStateType = Field(default=SMALStateType.NORMAL, description="The type of the state, which may affect its behavior and/or visualization.")
