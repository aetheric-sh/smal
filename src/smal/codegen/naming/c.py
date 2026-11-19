"""Module defining the C naming conventions for SMAL code generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from smal.codegen.primitives.language_primitive import get_language_primitive
from smal.utilities import constants as SMALConstants
from smal.utilities.types import SMALPrimitive

if TYPE_CHECKING:
    from smal.codegen.naming.language_naming_layer import LanguageNamingLayer
    from smal.schemas.debug import FieldSpec


class CLanguageNamingLayer:
    """Layer for C naming conventions."""

    @staticmethod
    def type_name(logical_name: str) -> str:
        """Get the name of a C type for a SMAL construct.

        Args:
            logical_name (str): The SMAL logical name.

        Returns:
            str: The C type name.

        """
        return f"{logical_name}_t"

    @staticmethod
    def field_decl(field: FieldSpec) -> str:
        """Get the C declaration of a struct field, without the trailing semicolon.

        Args:
            field (FieldSpec): The field to declare.

        Returns:
            str: The declaration, e.g. `uint16_t src_state`, `uint8_t payload[16]` or `smal_dbg_entry_t *entries`.

        """
        if field.ref:
            return f"{CLanguageNamingLayer.type_name(field.ref)}{' *' if field.array else ' '}{field.name}"
        wire = field.wire
        if wire.primitive == SMALPrimitive.BYTES:
            return f"uint8_t {field.name}[{wire.length}]"
        ctype = get_language_primitive(wire.primitive, SMALConstants.SupportedCodeLangs.C.value).name
        return f"{ctype} {field.name}"

    @staticmethod
    def enum_member(name: str, prefix: str = "") -> str:
        """Get the name of a C enum member.

        Args:
            name (str): The member's name.
            prefix (str, optional): The enum's namespace prefix, e.g. "dbg". Defaults to no prefix.

        Returns:
            str: The member name, e.g. `SMAL_DBG_ENTRY_TYPE_ERROR`.

        """
        return "_".join(part for part in (prefix, name) if part).upper()

    @staticmethod
    def enum_name(logical_name: str) -> str:
        """Get the C name of an enum, as distinct from its typedef name.

        Args:
            logical_name (str): The SMAL logical name.

        Returns:
            str: The C enum name.

        """
        return f"{logical_name}_e"

    @staticmethod
    def enum_count(logical_name: str) -> str:
        """Get the name of the member that terminates a C enum and holds its member count.

        Args:
            logical_name (str): The SMAL logical name of the enum.

        Returns:
            str: The terminating member name, e.g. `SMAL_DBG_ENTRY_TYPE_COUNT`.

        """
        return f"{logical_name}_count".upper()

    @staticmethod
    def enum_null(logical_name: str) -> str:
        """Get the name of the member that represents a null value (defined last, including after the count member if present).

        Args:
            logical_name (str): The enum's logical name.

        Returns:
            str: The null member name.

        """
        return f"{logical_name}_null".upper()


NAMING_LAYER: Final[type[LanguageNamingLayer]] = CLanguageNamingLayer
"""The naming layer `get_naming_layer` returns for C."""
