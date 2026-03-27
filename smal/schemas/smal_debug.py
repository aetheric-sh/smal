
from __future__ import annotations  # Until Python 3.14
from pydantic import BaseModel, Field, field_validator, model_validator
from smal.schemas.utilities import IdentifierValidationMixin
from typing import Literal
from typing_extensions import Self


PRIMITIVE_SIZES: dict[str, int] = {
    "uint8": 1,
    "int8": 1,
    "uint16": 2,
    "int16": 2,
    "uint32": 4,
    "int32": 4,
    "uint64": 8,
    "int64": 8,
    "bool": 1,
    "char": 1,
}


def sizeof_primitive(type_name: str) -> int:
    if type_name not in PRIMITIVE_SIZES:
        raise ValueError(f"Unknown primitive type: {type_name}")
    return PRIMITIVE_SIZES[type_name]


def base_type_and_kind(type_str: str) -> tuple[str, str]:
    if type_str.startswith("enum:"):
        return type_str.split(":", 1)[1], "enum"
    if type_str.startswith("struct:"):
        return type_str.split(":", 1)[1], "struct"
    return type_str, "primitive"

class SMALDebugBitField(IdentifierValidationMixin, BaseModel):
    IDENTIFIER_FIELDS = ("name",)

    name: str
    bit: int

    @field_validator("bit")
    def validate_bit(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Bit index must be >= 0")
        return v

class SMALDebugField(IdentifierValidationMixin, BaseModel):
    IDENTIFIER_FIELDS = ("name",)

    name: str = Field(..., description="The name of the debugging field.")
    type: str = Field(..., description="The type of the debugging field's data, e.g. uint8, uint16, enum:state, struct:Foo, etc.")
    offset_bytes: int | None = Field(default=None, description="The offset of this debugging field within its parent structure in bytes. If None, automatically calculated.")
    length_elements: int | None = Field(default=None, description="Length of the field in elements, if it is an array.")
    bitfields: list[SMALDebugBitField] | None = Field(default=None, description="Bit fields associated with this debug field, if this debug field is a bitfield.")
    endianness: Literal["big", "little"] = Field(default="little", description="Endianness of this debug field.")


    @field_validator("offset_bytes")
    def validate_offset_bytes(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("offset_bytes must be >= 0")
        return v

class SMALNestedDebugStruct(IdentifierValidationMixin, BaseModel):
    IDENTIFIER_FIELDS = ("name",)

    name: str = Field(..., description="The name of the debugging structure.")
    size_bytes: int = Field(..., description="The size of the entire debugging structure in bytes.")
    fields: list[SMALDebugField] = Field(..., description="Fields of the debugging structure.")

    @model_validator(mode="after")
    def validate_struct(self) -> Self:
        if self.size_bytes <= 0:
            raise ValueError(f"struct {self.name}: size_bytes must be > 0")
        return self

class SMALDebugStruct(BaseModel):
    size_bytes: int = Field(..., description="The size of the entire debugging structure in bytes.")
    layout: list[SMALDebugField] = Field(..., description="The layout of the debugging structure, defined by fields.")
    nested_structs: list[SMALNestedDebugStruct] = Field(default_factory=list, description="Nested debugging structures that are utilized in this debugging structure, if any.")

    @model_validator(mode="after")
    def validate_layout(self) -> Self:
        if self.size_bytes <= 0:
            raise ValueError(f"debug.size_bytes must be > 0")
        struct_map: dict[str, SMALNestedDebugStruct] = {s.name: s for s in self.nested_structs}
        current_offset_bytes = 0
        ranges: list[tuple[int, int, str]] = [] # (start, end, name)
        for field in self.layout:
            base, kind = base_type_and_kind(field.type)
            match kind:
                case "primitive":
                    elem_size = sizeof_primitive(base)
                case "struct":
                    if base not in struct_map:
                        raise ValueError(f"Field {field.name}: struct type '{base}' not defined in debug.nested_structs")
                    elem_size = struct_map[base].size_bytes
                case "enum":
                    elem_size = 1
                case _:
                    raise ValueError(f"Field {field.name}: unknown kind '{kind}'")
            length_elements = field.length_elements or 1
            if length_elements <= 0:
                raise ValueError(f"Field {field.name}: length_elements must be >= 1")
            if field.offset_bytes is None:
                field.offset_bytes = current_offset_bytes
            start = field.offset_bytes
            end = field.offset_bytes + elem_size * length_elements
            if start < 0 or end > self.size_bytes:
                raise ValueError(f"Field {field.name}: range [{start}, {end}) exceeds debug.size_bytes={self.size_bytes}")
            for (s, e, other_name) in ranges:
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