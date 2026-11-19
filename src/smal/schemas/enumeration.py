"""Module defining the Enumeration model for representing enumerations in a state machine."""

from __future__ import annotations  # Until Python 3.14

from functools import cached_property
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

from smal.schemas.debug import EnumSpec
from smal.utilities.types import Identifier, SMALPrimitive


class EnumMember(BaseModel):
    """An individual member of an Enumeration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    name: Identifier = Field(description="Enum member name.")
    value: StrictInt | None = Field(
        default=None,
        description="Explicit numeric value. If omitted, it is the previous member's value plus 1, and the first member defaults to 0 (as in C).",
    )
    description: StrictStr | None = Field(default=None, description="Description of the enum member.")

    @model_validator(mode="before")
    @classmethod
    def _from_shorthand(cls, data: Any) -> Any:
        return {"name": data} if isinstance(data, str) else data


class Enumeration(BaseModel):
    """An enumerated type that context variables can use as their `type`.

    Member names only need to be unique within their own enum, so two enums may both have a member called `none`, etc.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    name: Identifier = Field(description="Enum name.")
    values: list[EnumMember] = Field(min_length=1, description="Enum members, in order. Each may be a bare name or {name, value}.")
    description: str | None = Field(default=None, description="Description of the enum.")
    storage_type: SMALPrimitive = Field(
        default=SMALPrimitive.UINT8,
        description="Fixed-width integer type used to store this enum in generated code. Every member's value must fit in it.",
    )

    @property
    def resolved_values(self) -> dict[str, int]:
        """Get each member name mapped to its numeric value, with omitted values auto-numbered as in C.

        Returns:
            dict[str, int]: The member name to resolved numeric value, in definition order.

        """
        resolved: dict[str, int] = {}
        next_value = 0
        for member in self.values:
            value = next_value if member.value is None else member.value
            resolved[member.name] = value
            next_value = value + 1
        return resolved

    @cached_property
    def spec(self) -> EnumSpec:
        return EnumSpec.build_from_data(
            data=self.resolved_values,
            name=self.name,
            prefix=self.name,
            include_count=True,
            include_null=False,
        )

    @model_validator(mode="after")
    def _enforce_unique_members(self) -> Enumeration:
        names = [m.name for m in self.values]
        duplicate_names = sorted({n for n in names if names.count(n) > 1})
        if duplicate_names:
            raise ValueError(f"Enum '{self.name}' has duplicate member names: {duplicate_names}.")
        numbers = list(self.resolved_values.values())
        duplicate_numbers = sorted({v for v in numbers if numbers.count(v) > 1})
        if duplicate_numbers:
            raise ValueError(f"Enum '{self.name}' has members sharing the numeric values {duplicate_numbers}. Give them distinct explicit values.")
        return self

    @model_validator(mode="after")
    def _enforce_storage_type(self) -> Enumeration:
        if not self.storage_type.is_integer:
            raise ValueError(f"Enum '{self.name}' storage_type must be a fixed-width integer (uint8 to int64), not '{self.storage_type.value}'.")
        for member_name, value in self.resolved_values.items():
            try:
                self.storage_type.check_value(value)
            except ValueError as exc:
                raise ValueError(f"Enum '{self.name}' member '{member_name}' does not fit its storage_type: {exc}") from exc
        return self
