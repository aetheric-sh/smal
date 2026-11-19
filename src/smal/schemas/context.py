from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, JsonValue, PrivateAttr

from smal.schemas.enumeration import Enumeration, EnumMember  # noqa: TC001 - Pydantic requires this at runtime
from smal.utilities.types import Identifier, LabeledIdentifier, SMALPrimitive  # noqa: TC001 - Pydantic requires this at runtime


class ContextVar(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    name: Identifier = Field(description="Name of the context variable.")
    type: LabeledIdentifier = Field(description="Datatype of the context variable.")
    default_value: JsonValue = Field(description="Default value.")
    value_constraints: list[JsonValue] | None = Field(default=None, description="Value constraints.")
    _resolved_type: SMALPrimitive | Enumeration | None = PrivateAttr(default=None)
    _resolved_value: JsonValue | EnumMember | None = PrivateAttr(default=None)

    @property
    def resolved_type(self) -> SMALPrimitive | Enumeration | None:
        return self._resolved_type

    @property
    def resolved_value(self) -> JsonValue | EnumMember | None:
        return self._resolved_value

    def set_resolved_type(self, t: SMALPrimitive | Enumeration):
        self._resolved_type = t

    def set_resolved_value(self, v: JsonValue | EnumMember):
        self._resolved_value = v
