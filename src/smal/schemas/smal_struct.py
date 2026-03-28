from __future__ import annotations  # Until Python 3.14

from typing import ClassVar, Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self

from smal.codegen import get_target_primitive
from smal.schemas.smal_bitfield import SMALBitField
from smal.schemas.smal_enum import SMALEnum
from smal.schemas.utilities import IdentifierValidationMixin, PrimitiveValidationMixin
from smal.smal_primitive import SMALPrimitive
from smal.utilities import constants as SMALConstants


class SMALStructField(IdentifierValidationMixin, PrimitiveValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)
    TYPE_FIELDS: ClassVar[tuple[str]] = ("type",)

    name: str = Field(..., description="The name of the debugging field.")
    type: str = Field(..., description="The type of the debugging field's data, e.g. uint8, uint16, enum:state, struct:Foo, etc.")
    offset_bytes: int | None = Field(default=None, description="The offset of this debugging field within its parent structure in bytes. If None, automatically calculated.")
    length_elements: int | None = Field(default=None, description="Length of the field in elements, if it is an array.")
    bitfields: list[SMALBitField] | None = Field(default=None, description="Bit fields associated with this debug field, if this debug field is a bitfield.")
    endianness: Literal["big", "little"] = Field(default="little", description="Endianness of this debug field.")

    @field_validator("offset_bytes")
    def validate_offset_bytes(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("offset_bytes must be >= 0")
        return v


class SMALNestedStruct(IdentifierValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str = Field(..., description="The name of the structure.")
    size_bytes: int = Field(..., description="The size of the entire structure in bytes.")
    layout: list[SMALStructField] = Field(..., description="Fields of the structure.")

    @model_validator(mode="after")
    def validate_struct(self) -> Self:
        if self.size_bytes <= 0:
            raise ValueError(f"struct {self.name}: size_bytes must be > 0")
        return self


class SMALStruct(BaseModel):
    lang: str = Field(..., description="The language this struct will be defined in, e.g., c, cpp, rust, etc.")
    size_bytes: int = Field(..., description="The size of the entire structure in bytes.")
    layout: list[SMALStructField] = Field(..., description="The layout of the structure, defined by fields.")
    nested_structs: list[SMALNestedStruct] = Field(default_factory=list, description="Nested structures that are utilized in this structure, if any.")
    enums: list[SMALEnum] = Field(default_factory=list, description="Enumerations defined for fields of the structure, if any.")

    @field_validator("lang")
    def validate_lang(cls, v: str) -> str:
        if not SMALConstants.SupportedCodeLangs.is_supported_lang(v):
            raise ValueError(f"Language is not supported: '{v}'. Supported languages are: {', '.join(SMALConstants.SupportedCodeLangs.all())}")
        return v

    @model_validator(mode="after")
    def validate_layout(self) -> Self:
        if self.size_bytes <= 0:
            raise ValueError("debug.size_bytes must be > 0")
        struct_map: dict[str, SMALNestedStruct] = {s.name: s for s in self.nested_structs}
        enum_map: dict[str, SMALEnum] = {e.name: e for e in self.enums}
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
                        raise ValueError(f"Field {field.name}: struct type '{base}' not defined in debug.nested_structs")
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
