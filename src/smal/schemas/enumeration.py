"""Enumerations for a state machine's associated data."""

from __future__ import annotations  # Until Python 3.14

from typing import Any, ClassVar

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

from smal.schemas.debug import EnumSpec
from smal.utilities.types import Identifier, SMALPrimitive


class EnumMember(BaseModel):
    """An individual member of an Enumeration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    name: Identifier = Field(description="Enum member name.")
    value: StrictInt | None = Field(
        default=None,
        validation_alias=AliasChoices("value", "id"),
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
    flags: bool = Field(default=False, description="Whether this enum is a bitmask (flags) enum. If true, members should be powers of two.")
    include_null: bool = Field(default=False, description="Whether to generate a null member.")
    include_count: bool = Field(default=False, description="Whether to generate a count member.")

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

    @model_validator(mode="after")
    def _enforce_unique_members(self) -> Enumeration:
        names = [m.name for m in self.values]
        if self.include_null:
            names.append("null")
        if self.include_count:
            names.append("count")
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

    @model_validator(mode="after")
    def _enforce_flags(self) -> Enumeration:
        if self.flags:
            for member_name, value in self.resolved_values.items():
                if value != 0 and (value & (value - 1)) != 0:
                    raise ValueError(
                        f"Enum '{self.name}' member '{member_name}' has value {value},"
                        " which is not a power of two. All members of a flags enum must be powers of two."
                    )
        return self

    def specification(self, prefix: str | None = None) -> EnumSpec:
        """Get the enumeration specification for this enumeration.

        Args:
            prefix (str | None): Optional prefix to prepend to each member name in the spec. Defaults to the enum's name.

        Returns:
            EnumSpec: The enumeration specification.

        """
        return EnumSpec.build_from_data(
            self.resolved_values,
            name=self.name,
            storage=self.storage_type,
            flags=self.flags,
            prefix=prefix or "",
            include_count=self.include_count,
            include_null=self.include_null,
        )
