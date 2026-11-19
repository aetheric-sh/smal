"""Protocol for the naming conventions that each target language provides to code generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pydantic import JsonValue

    from smal.schemas.debug import EnumSpec, FieldSpec
    from smal.schemas.enumeration import Enumeration, EnumMember
    from smal.utilities.types import SMALPrimitive


class LanguageNamingLayer(Protocol):
    """The naming conventions of one target language. Templates reach these as `<lang>_<name>` Jinja filters, e.g. `c_type_name`."""

    @staticmethod
    def type_name(logical_name: str) -> str:
        """Get the name of the language's type for a SMAL construct (struct, union or enum)."""
        ...

    @staticmethod
    def field_decl(field: FieldSpec) -> str:
        """Get the declaration of a struct field, e.g. `uint16_t src_state`."""
        ...

    @staticmethod
    def enum_member(name: str, prefix: str = "") -> str:
        """Get the name of an enum member. The name comes first so this works as a Jinja filter, e.g. `member | c_enum_member(prefix)`."""
        ...

    @staticmethod
    def enum_name(logical_name: str) -> str:
        """Get the name of an enum, where the language distinguishes it from the type name."""
        ...

    @staticmethod
    def enum_count(logical_name: str) -> str:
        """Get the name of the terminating member that holds the number of enum members."""
        ...

    @staticmethod
    def enum_null(logical_name: str) -> str:
        """Get the null member name."""
        ...

    @staticmethod
    def primitive_datatype(smal_primitive: str | SMALPrimitive) -> str:
        """Get the datatype for a primitive."""
        ...

    @staticmethod
    def primitive_value(t: SMALPrimitive | Enumeration, v: JsonValue | EnumMember, enum_specs: list[EnumSpec] | None = None) -> str:
        """Get the literal value for a primitive or enum."""
        ...
