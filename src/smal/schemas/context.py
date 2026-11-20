"""Schema for a state machine context variable defined in a SMAL (yaml) file."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, JsonValue, PrivateAttr

from smal.schemas.enumeration import Enumeration, EnumMember  # noqa: TC001 - Pydantic requires this at runtime
from smal.utilities.types import Identifier, LabeledIdentifier, SMALPrimitive  # noqa: TC001 - Pydantic requires this at runtime


class ContextVar(BaseModel):
    """Context variable utilized by a state machine for state management and guards."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    name: Identifier = Field(description="Name of the context variable.")
    type: LabeledIdentifier = Field(description="Datatype of the context variable.")
    default_value: JsonValue = Field(description="Default value.")
    value_constraints: list[JsonValue] | None = Field(default=None, description="Value constraints.")
    _resolved_type: SMALPrimitive | Enumeration | None = PrivateAttr(default=None)
    _resolved_value: JsonValue | EnumMember | None = PrivateAttr(default=None)

    @property
    def resolved_type(self) -> SMALPrimitive | Enumeration | None:
        """Get the resolved type of this context variable.

        Returns:
            SMALPrimitive | Enumeration | None: The resolved type of this context variable, or None if it has not been resolved yet.

        """
        return self._resolved_type

    @property
    def resolved_value(self) -> JsonValue | EnumMember | None:
        """Get the resolved value of this context variable.

        Returns:
            JsonValue | EnumMember | None: The resolved value of this context variable, or None if it has not been resolved yet.

        """
        return self._resolved_value

    def set_resolved_type(self, t: SMALPrimitive | Enumeration) -> None:
        """Set the resolved type of this context variable.

        Args:
            t (SMALPrimitive | Enumeration): The resolved type to set for this context variable.

        """
        self._resolved_type = t

    def set_resolved_value(self, v: JsonValue | EnumMember) -> None:
        """Set the resolved value of this context variable.

        Args:
            v (JsonValue | EnumMember): The resolved value to set for this context variable.

        """
        self._resolved_value = v
