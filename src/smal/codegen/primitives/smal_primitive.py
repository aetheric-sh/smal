"""Module defining the SMALPrimitive enumeration, which represents the primitive types defined in the SMAL standard."""

from __future__ import annotations  # Until Python 3.14

from enum import Enum


class SMALPrimitive(str, Enum):
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
    ENUM = "enum"  # For SMAL-defined enums (debugging)
    STRUCT = "struct"  # For SMAL-defined structs (debugging)

    @staticmethod
    def is_smal_primitive(s: str) -> bool:
        """Get whether the given string represents a SMAL primitive.

        Args:
            s (str): The string to validate.

        Returns:
            bool: True if the given str is a SMAL primitive, False otherwise.

        """
        if "enum:" in s or "struct:" in s:
            return True
        return s in {member.value for member in SMALPrimitive}

    @property
    def is_debug_primitive(self) -> bool:
        """Get whether this SMALPrimitive is a debugging primitive (an enum or struct).

        Returns:
            bool: True if this SMALPrimitive is a debugging primitive, False otherwise.

        """
        return self in {SMALPrimitive.ENUM, SMALPrimitive.STRUCT}

    @staticmethod
    def from_str(s: str) -> tuple[SMALPrimitive, str | None]:
        """Create a SMALPrimitive and optionally, its base name from a string.

        Args:
            s (str): The string to create a SMALPrimitive from.

        Returns:
            tuple[SMALPrimitive, str | None]: The resulting SMALPrimitive and, if applicable, its base.

        """
        if "enum:" in s:
            base = s.split(":", 1)[1]
            return SMALPrimitive.ENUM, base
        if "struct:" in s:
            base = s.split(":", 1)[1]
            return SMALPrimitive.STRUCT, base
        return SMALPrimitive(s), None
