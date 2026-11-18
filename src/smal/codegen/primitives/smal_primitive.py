"""Module defining the SMALPrimitive enumeration, which represents the primitive types defined in the SMAL standard."""

from __future__ import annotations  # Until Python 3.14

from enum import StrEnum


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
    def is_debug_primitive(self) -> bool:
        """Get whether this SMALPrimitive is a debugging primitive (an enum).

        Returns:
            bool: True if this SMALPrimitive is a debugging primitive, False otherwise.

        """
        return self == SMALPrimitive.ENUM

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
        layout = _INTEGER_LAYOUTS.get(self)
        if layout is None:
            return None
        bits, signed = layout
        return -(2 ** (bits - 1)) if signed else 0

    @property
    def max_value(self) -> int | None:
        """Get the largest value this fixed-width integer can hold.

        Returns:
            int | None: The maximum value, or None if this is not a fixed-width integer.

        """
        layout = _INTEGER_LAYOUTS.get(self)
        if layout is None:
            return None
        bits, signed = layout
        return 2 ** (bits - 1) - 1 if signed else 2**bits - 1

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


# Width in bits and signedness of each fixed-width integer
_INTEGER_LAYOUTS: dict[SMALPrimitive, tuple[int, bool]] = {
    SMALPrimitive.UINT8: (8, False),
    SMALPrimitive.INT8: (8, True),
    SMALPrimitive.UINT16: (16, False),
    SMALPrimitive.INT16: (16, True),
    SMALPrimitive.UINT32: (32, False),
    SMALPrimitive.INT32: (32, True),
    SMALPrimitive.UINT64: (64, False),
    SMALPrimitive.INT64: (64, True),
}
