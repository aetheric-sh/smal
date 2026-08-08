"""Module defining the schema for a structure in SMAL, including its fields, substructures, and enumerations."""

from __future__ import annotations  # Until Python 3.14

from typing import ClassVar, Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self

from smal.codegen.target_primitive import get_target_primitive
from smal.schemas.bit_field import BitField  # noqa: TC001 - Pydantic requires this at runtime for type validation
from smal.schemas.enumeration import Enumeration  # noqa: TC001 - Pydantic requires this at runtime for type validation
from smal.schemas.utilities import IdentifierValidationMixin, PrimitiveValidationMixin
from smal.codegen.primitives.smal_primitive import SMALPrimitive
from smal.utilities import constants as SMALConstants


class StructField(IdentifierValidationMixin, PrimitiveValidationMixin, BaseModel):
    """Model describing a field within a struct."""

    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)
    TYPE_FIELDS: ClassVar[tuple[str]] = ("type",)

    name: str = Field(..., description="The name of the debugging field.")
    type: str = Field(..., description="The type of the debugging field's data, e.g. uint8, uint16, enum:state, struct:Foo, etc.")
    offset_bytes: int | None = Field(
        default=None,
        description="The offset of this debugging field within its parent structure in bytes. If None, automatically calculated.",
    )
    length_elements: int | None = Field(default=None, description="Length of the field in elements, if it is an array.")
    bitfields: list[BitField] | None = Field(default=None, description="Bit fields associated with this debug field, if this debug field is a bitfield.")
    endianness: Literal["big", "little"] = Field(default="little", description="Endianness of this debug field.")

    @field_validator("offset_bytes")
    @classmethod
    def validate_offset_bytes(cls, v: int | None) -> int | None:
        """Validate the offset bytes field.

        Args:
            v (int | None): The value of the offset_bytes field to validate.

        Raises:
            ValueError: If the offset_bytes value is negative.

        Returns:
            int | None: The validated offset_bytes value.

        """
        if v is not None and v < 0:
            raise ValueError("offset_bytes must be >= 0")
        return v


class Struct(IdentifierValidationMixin, BaseModel):
    """Model describing a structure in SMAL."""

    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)
    name: str = Field(..., description="The name of the structure.")
    lang: str = Field(..., description="The language this struct will be defined in, e.g., c, cpp, rust, etc.")
    size_bytes: int = Field(..., description="The size of the entire structure in bytes.")
    layout: list[StructField] = Field(..., description="The layout of the structure, defined by fields.")
    substructs: list[Struct] = Field(default_factory=list, description="Nested structures that are utilized in this structure, if any.")
    enums: list[Enumeration] = Field(default_factory=list, description="Enumerations defined for fields of the structure, if any.")

    @field_validator("lang")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        """Validate that the given language is a supported language.

        Args:
            v (str): The language to validate.

        Raises:
            ValueError: If the language is not supported.

        Returns:
            str: The validated language.

        """
        if not SMALConstants.SupportedCodeLangs.is_supported_lang(v):
            raise ValueError(f"Language is not supported: '{v}'. Supported languages are: {', '.join(SMALConstants.SupportedCodeLangs.all())}")
        return v

    @model_validator(mode="after")
    def validate_layout(self) -> Self:
        """Validate the overall layout of the structure.

        Raises:
            ValueError: If the size_bytes is not greater than 0.
            ValueError: If a field's type is an enum but the enum is not defined in debug.enums.
            ValueError: If a field's type is a struct but the struct is not defined in debug.substructs.
            ValueError: If a field's length_elements is not greater than 0.
            ValueError: If a field's range exceeds the structure's size_bytes.
            ValueError: If a field overlaps with another field.
            ValueError: If a bitfield's bit index exceeds the capacity of its base type.

        Returns:
            Self: The validated structure instance.

        """
        if self.size_bytes <= 0:
            raise ValueError("debug.size_bytes must be > 0")
        struct_map: dict[str, Struct] = {s.name: s for s in self.substructs}
        enum_map: dict[str, Enumeration] = {e.name: e for e in self.enums}
        current_offset_bytes = 0
        ranges: list[tuple[int, int, str]] = []  # (start, end, name)
        for field in self.layout:
            smal_type = SMALPrimitive.from_str(field.type)
            kind, base = smal_type
            match kind:
                case SMALPrimitive.ENUM:
                    if base not in enum_map:
                        raise ValueError(f"Field {field.name}: enum type '{base}' not defined in debug.enums")
                    elem_size = 1  # Enums default to uint8
                case SMALPrimitive.STRUCT:
                    if base not in struct_map:
                        raise ValueError(f"Field {field.name}: struct type '{base}' not defined in debug.substructs")
                    elem_size = struct_map[base].size_bytes
                case _:
                    lang_local_primitive = get_target_primitive(kind, self.lang)
                    elem_size = lang_local_primitive.size_bytes
            length_elements = field.length_elements or 1
            if length_elements <= 0:
                raise ValueError(f"Field {field.name}: length_elements must be >= 1")
            if field.offset_bytes is None:
                field.offset_bytes = current_offset_bytes
            start = field.offset_bytes
            end = field.offset_bytes + elem_size * length_elements
            if start < 0 or end > self.size_bytes:
                raise ValueError(f"Field {field.name}: range [{start}, {end}) exceeds debug.size_bytes={self.size_bytes}")
            for s, e, other_name in ranges:
                if not (end <= s or start >= e):
                    raise ValueError(f"Field {field.name} overlaps with field {other_name}: [{start}, {end}) vs [{s}, {e})")
            ranges.append((start, end, field.name))
            current_offset_bytes = max(current_offset_bytes, end)
            if field.bitfields:
                max_bit = max(bf.bit for bf in field.bitfields)
                bit_capacity = elem_size * 8
                if max_bit >= bit_capacity:
                    raise ValueError(f"Field {field.name}: bitfield bit index {max_bit} exceeds capacity of base type ({bit_capacity} bits)")
        return self
