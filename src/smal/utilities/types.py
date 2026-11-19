"""Reusable types for SMAL."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import TYPE_CHECKING, Annotated, Any, Protocol

import semver
from annotated_types import Ge, GroupedMetadata, Le, MaxLen, MinLen
from pydantic import BeforeValidator, Field, PlainSerializer, StrictBool, StrictFloat, StrictInt, WithJsonSchema

if TYPE_CHECKING:
    from collections.abc import Iterator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")]
"""String representing an identifier."""

LabeledIdentifier = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*(?::[A-Za-z][A-Za-z0-9_]*)?$")]
"""String representing an identifier with an optional label of the form <label>:<identifier>."""


def _parse_semver(v: Any) -> semver.Version:
    if isinstance(v, semver.Version):
        return v
    return semver.Version.parse(str(v))  # Raises ValueError on bad input


SemVer = Annotated[
    semver.Version,
    BeforeValidator(_parse_semver),
    PlainSerializer(str, return_type=str),
    WithJsonSchema({"type": "string", "format": "semver"}),
]
"""A parsed and validated semantic version (major.minor.patch). Serializes to string."""


class IdentifiableObject(Protocol):
    """Protocol for objects with name and id."""

    name: Identifier
    id: StrictInt | None


class SMALPrimitive(StrEnum):
    """Enumeration of SMAL-standard primitive types. To be mapped to each target language (C, C++, Rust)."""

    UINT8 = "uint8"
    INT8 = "int8"
    UINT16 = "uint16"
    INT16 = "int16"
    UINT32 = "uint32"
    INT32 = "int32"
    UINT64 = "uint64"
    INT64 = "int64"
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    BOOL = "bool"
    CHAR8 = "char8"  # Alias for uint8
    BYTE = "byte"  # Alias for uint8
    BYTES = "bytes"  # Alias for array of uint8
    ENUM = "enum"  # For SMAL-defined enums. Written `enum:<name>`, where <name> is the enum's name.

    @staticmethod
    def is_smal_primitive(s: str) -> bool:
        """Get whether the given string represents a SMAL primitive.

        Args:
            s (str): The string to validate.

        Returns:
            bool: True if the given str is a SMAL primitive (including `enum:<name>` with a non-empty name), False otherwise.

        """
        if s.startswith("enum:"):
            return bool(s.partition(":")[2])
        return s in {member.value for member in SMALPrimitive}

    @property
    def is_integer(self) -> bool:
        """Get whether this SMALPrimitive is a fixed-width integer (uint8 through int64).

        Returns:
            bool: True if this is a fixed-width integer, False otherwise. The `char8` and `byte` aliases are not counted.

        """
        return self in _INTEGER_LAYOUTS

    @property
    def is_float(self) -> bool:
        """Get whether this SMALPrimitive is a floating point type.

        Returns:
            bool: True for float32 and float64, False otherwise.

        """
        return self in {SMALPrimitive.FLOAT32, SMALPrimitive.FLOAT64}

    @property
    def bit_width(self) -> int | None:
        """Get the width in bits of this fixed-width integer.

        Returns:
            int | None: The width in bits, or None if this is not a fixed-width integer.

        """
        layout = _INTEGER_LAYOUTS.get(self)
        return layout[0] if layout else None

    @property
    def min_value(self) -> int | None:
        """Get the smallest value this fixed-width integer can hold.

        Returns:
            int | None: The minimum value, or None if this is not a fixed-width integer.

        """
        return _INTEGER_RANGES.get(self)[0] if self in _INTEGER_RANGES else None

    @property
    def max_value(self) -> int | None:
        """Get the largest value this fixed-width integer can hold.

        Returns:
            int | None: The maximum value, or None if this is not a fixed-width integer.

        """
        return _INTEGER_RANGES.get(self)[1] if self in _INTEGER_RANGES else None

    @property
    def struct_code(self) -> str | None:
        """Get the struct packing code of this primitive, if applicable.

        Returns:
            str | None: The struct code, or None if not applicable.

        """
        return _STRUCT_CODES.get(self)

    def check_value(self, value: object) -> None:
        """Check that a value can be stored in this primitive.

        Args:
            value (object): The value to check.

        Raises:
            ValueError: If the value has the wrong type, is out of range for this integer type, or this primitive does not support value checks.

        """
        if self == SMALPrimitive.BOOL:
            if not isinstance(value, bool):
                raise ValueError(f"{value!r} is not a bool.")
        elif self.is_integer:
            # bool is a subclass of int in Python, but True is not a sensible value for a counter
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{value!r} is not an integer, which {self.value} requires.")
            if not self.min_value <= value <= self.max_value:
                raise ValueError(f"{value} is out of range for {self.value} ({self.min_value} to {self.max_value}).")
        elif self.is_float:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{value!r} is not a number, which {self.value} requires.")
        else:
            raise ValueError(f"Values of type {self.value} cannot be checked.")

    @staticmethod
    def from_str(s: str) -> tuple[SMALPrimitive, str | None]:
        """Create a SMALPrimitive and optionally, its base name from a string.

        Args:
            s (str): The string to create a SMALPrimitive from. For enums this is `enum:<name>`.

        Raises:
            ValueError: If the string is not a SMAL primitive, or is `enum:` with no enum name.

        Returns:
            tuple[SMALPrimitive, str | None]: The resulting SMALPrimitive and, for enums, the enum's name.

        """
        if s.startswith("enum:"):
            base = s.partition(":")[2]
            if not base:
                raise ValueError("An enum primitive needs the enum's name, e.g. 'enum:Foo'.")
            return SMALPrimitive.ENUM, base
        return SMALPrimitive(s), None


@dataclass(frozen=True)
class WireType:
    """Metadata representing a wire type."""

    primitive: SMALPrimitive
    length: int | None = None  # fixed size, for bytes
    enum_name: str | None = None  # for SMALPrimitive.ENUM

    def __post_init__(self) -> None:
        """Validate the construction of WireType.

        Raises:
            ValueError: If the length is not set on a bytes primitive.
            ValueError: If the length is not positive.
            ValueError: If the enum name is missing for enums.

        """
        if (self.primitive == SMALPrimitive.BYTES) != (self.length is not None):
            raise ValueError("Length must be set for bytes.")
        if self.length is not None and self.length < 1:
            raise ValueError("Length must be positive.")
        if (self.primitive == SMALPrimitive.ENUM) != (self.enum_name is not None):
            raise ValueError("Enum name must be set for enums.")


UInt8 = Annotated[StrictInt, Ge(0), Le(0xFF), WireType(SMALPrimitive.UINT8)]
Int8 = Annotated[StrictInt, Ge(-0x80), Le(0x7F), WireType(SMALPrimitive.INT8)]
UInt16 = Annotated[StrictInt, Ge(0), Le(0xFFFF), WireType(SMALPrimitive.UINT16)]
Int16 = Annotated[StrictInt, Ge(-0x8000), Le(0x7FFF), WireType(SMALPrimitive.INT16)]
UInt32 = Annotated[StrictInt, Ge(0), Le(0xFFFFFFFF), WireType(SMALPrimitive.UINT32)]
Int32 = Annotated[StrictInt, Ge(-0x80000000), Le(0x7FFFFFFF), WireType(SMALPrimitive.INT32)]
UInt64 = Annotated[StrictInt, Ge(0), Le(0xFFFFFFFFFFFFFFFF), WireType(SMALPrimitive.UINT64)]
Int64 = Annotated[StrictInt, Ge(-0x8000000000000000), Le(0x7FFFFFFFFFFFFFFF), WireType(SMALPrimitive.INT64)]
Float32 = Annotated[StrictFloat, WireType(SMALPrimitive.FLOAT32)]
Float64 = Annotated[StrictFloat, WireType(SMALPrimitive.FLOAT64)]
Bool = Annotated[StrictBool, WireType(SMALPrimitive.BOOL)]
Char8 = Annotated[str, Field(min_length=1, max_length=1, pattern=r"^[\x00-\xFF]$"), WireType(SMALPrimitive.CHAR8)]
Byte = Annotated[StrictInt, Ge(0), Le(0xFF), WireType(SMALPrimitive.BYTE)]


@dataclass(frozen=True)
class FixedBytes(GroupedMetadata):
    """Bundle of metadata representing a fixed-size byte array."""

    length: int

    def __iter__(self) -> Iterator[object]:
        """Iterate through the pieces of metadata this GroupedMetadata offers.

        Yields:
            Iterator[object]: The metadata pieces.

        """
        yield MinLen(self.length)
        yield MaxLen(self.length)
        yield WireType(SMALPrimitive.BYTES, length=self.length)


def EnumOf(enum: type[Enum] | str) -> WireType:
    """Create a WireType representing `enum`.

    Args:
        enum (type[Enum] | str): The enum type or its name.

    Returns:
        WireType: The enum wire type.

    """
    name = enum if isinstance(enum, str) else enum.__name__
    return WireType(SMALPrimitive.ENUM, enum_name=name)


@dataclass(frozen=True)
class RefTo:
    """Metadata marking a field whose type is another generated type (struct or tagged union), referenced by its logical name."""

    name: str
    array: bool = False  # The field is a runtime-sized array of the referenced type
    count_field: str | None = None  # For arrays: the sibling field that holds the number of elements

    def __post_init__(self) -> None:
        """Validate the construction of RefTo.

        Raises:
            ValueError: If the name is empty.
            ValueError: If a count field is given for something that is not an array.

        """
        if not self.name:
            raise ValueError("RefTo needs the name of the type it refers to.")
        if self.count_field is not None and not self.array:
            raise ValueError("count_field is only valid for arrays.")


# Minimum and maximum values for integers
_INTEGER_RANGES: dict[SMALPrimitive, tuple[int, int]] = {
    SMALPrimitive.BYTE: (0, 0xFF),
    SMALPrimitive.CHAR8: (0, 0xFF),
    SMALPrimitive.UINT8: (0, 0xFF),
    SMALPrimitive.INT8: (-0x80, 0x7F),
    SMALPrimitive.UINT16: (0, 0xFFFF),
    SMALPrimitive.INT16: (-0x8000, 0x7FFF),
    SMALPrimitive.UINT32: (0, 0xFFFFFFFF),
    SMALPrimitive.INT32: (-0x80000000, 0x7FFFFFFF),
    SMALPrimitive.UINT64: (0, 0xFFFFFFFFFFFFFFFF),
    SMALPrimitive.INT64: (-0x8000000000000000, 0x7FFFFFFFFFFFFFFF),
}

# Width in bits and signedness of each fixed-width integer
_INTEGER_LAYOUTS: dict[SMALPrimitive, tuple[int, bool]] = {
    SMALPrimitive.BYTE: (8, False),
    SMALPrimitive.CHAR8: (8, False),
    SMALPrimitive.UINT8: (8, False),
    SMALPrimitive.INT8: (8, True),
    SMALPrimitive.UINT16: (16, False),
    SMALPrimitive.INT16: (16, True),
    SMALPrimitive.UINT32: (32, False),
    SMALPrimitive.INT32: (32, True),
    SMALPrimitive.UINT64: (64, False),
    SMALPrimitive.INT64: (64, True),
}

_STRUCT_CODES: dict[SMALPrimitive, str] = {
    SMALPrimitive.BYTE: "B",
    SMALPrimitive.CHAR8: "B",
    SMALPrimitive.UINT8: "B",
    SMALPrimitive.INT8: "b",
    SMALPrimitive.UINT16: "H",
    SMALPrimitive.INT16: "h",
    SMALPrimitive.UINT32: "I",
    SMALPrimitive.INT32: "i",
    SMALPrimitive.UINT64: "Q",
    SMALPrimitive.INT64: "q",
    SMALPrimitive.FLOAT32: "f",
    SMALPrimitive.FLOAT64: "d",
    SMALPrimitive.BOOL: "?",
}
