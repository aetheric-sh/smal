"""Module defining the schema for the debug structures for SMAL state machines, independent of any target language."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import Enum, Flag, IntFlag
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

from pydantic import BaseModel, Field

from smal.utilities.types import Bool, IdentifiableObject, Int16, Int32, RefTo, SMALPrimitive, UInt16, UInt32, WireType

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from smal.schemas.machine import Machine


class SMALDebugEntryType(IntFlag):
    """Enumeration of debug entry types (bitfield flags)."""

    ENTRY_TYPE_NONE = 0
    ENTRY_TYPE_STATE_TRANSITION = 1 << 0
    ENTRY_TYPE_EVENT_RX = 1 << 1
    ENTRY_TYPE_EVENT_TX = 1 << 2
    ENTRY_TYPE_CMD_RX = 1 << 3
    ENTRY_TYPE_CMD_TX = 1 << 4
    ENTRY_TYPE_DATA_READ = 1 << 5
    ENTRY_TYPE_DATA_WRITE = 1 << 6
    ENTRY_TYPE_ERROR = 1 << 7
    # Additional types can be added as needed

    @staticmethod
    def formatted_display(entry_type: int) -> str:
        """Return a human-readable string representation of the entry type bitmask.

        Args:
            entry_type: The entry_type bitmask to format.

        Returns:
            A string listing the entry types represented by the bitmask.

        """
        types = []
        if entry_type & SMALDebugEntryType.ENTRY_TYPE_STATE_TRANSITION:
            types.append("TRANSITION")
        if entry_type & SMALDebugEntryType.ENTRY_TYPE_EVENT_RX:
            types.append("EVT_RX")
        if entry_type & SMALDebugEntryType.ENTRY_TYPE_EVENT_TX:
            types.append("EVT_TX")
        if entry_type & SMALDebugEntryType.ENTRY_TYPE_CMD_RX:
            types.append("CMD_RX")
        if entry_type & SMALDebugEntryType.ENTRY_TYPE_CMD_TX:
            types.append("CMD_TX")
        if entry_type & SMALDebugEntryType.ENTRY_TYPE_DATA_READ:
            types.append("DATA_RD")
        if entry_type & SMALDebugEntryType.ENTRY_TYPE_DATA_WRITE:
            types.append("DATA_WR")
        if entry_type & SMALDebugEntryType.ENTRY_TYPE_ERROR:
            types.append("ERROR")
        return ", ".join(types) if types else "NONE"


def _name_for(items: Sequence[IdentifiableObject], item_id: int) -> str | None:
    """Get the name of the item whose id (or, if it has none, its index) is `item_id`.

    Args:
        items (Sequence[IdentifiableObject]): Objects with `name` and `id` attributes, e.g. `Machine.states`.
        item_id (int): The id to look up.

    Returns:
        str | None: The item's name, or None if no item has that id.

    """
    return next((item.name for idx, item in enumerate(items) if (idx if item.id is None else item.id) == item_id), None)


def _label(items: Sequence[IdentifiableObject], kind: str, item_id: int) -> str:
    """Get `name(id)` for an item, or `kind#id(id)` if it can't be resolved.

    Args:
        items (Sequence[IdentifiableObject]): Objects with `name` and `id` attributes, e.g. `Machine.states`.
        kind (str): What the items are (e.g. "state"), used in the fallback name.
        item_id (int): The id to look up.

    Returns:
        str: The label.

    """
    return f"{_name_for(items, item_id) or f'{kind}#{item_id}'}({item_id})"


class SMALDebugTransitionPayload(BaseModel):
    """Payload for state transition debug entries."""

    entry_type: Literal["transition"] = Field(default="transition", exclude=True)
    src_state: UInt16 = Field(description="Source state ID or index before the transition.")
    tgt_state: UInt16 = Field(description="Target state ID or index after the transition.")
    evt: UInt16 = Field(description="Event ID or index that triggered the transition.")
    status: Int16 = Field(description="Status of the transition (success, failure, error code, etc.).")

    def display(self, sm: Machine) -> str:
        """Return a human-readable representation of this payload.

        Args:
            sm (Machine): The state machine to resolve against.

        Returns:
            str: Human-readable representation of the payload.

        """
        status = "OK(0)" if self.status == 0 else _label(sm.errors, "error", self.status)
        src_state = _label(sm.states, "state", self.src_state)
        evt = _label(sm.events, "event", self.evt)
        tgt_state = _label(sm.states, "state", self.tgt_state)
        return f"{src_state} --[{evt}]--> {tgt_state} · {status}"


class SMALDebugMessagePayload(BaseModel):
    """Payload for event/command debug entries."""

    entry_type: Literal["message"] = Field(default="message", exclude=True)
    identifier: UInt16 = Field(description="Event or command ID/index.")
    data_len: UInt16 = Field(description="Length of data associated with the event or command, in bytes.")
    value: UInt32 = Field(description="Value associated with the event or command (parameter, status code, etc.).")

    def display(self, sm: Machine) -> str:
        """Return a human-readable representation of this payload.

        Args:
            sm (Machine): The state machine to resolve against.

        Returns:
            str: Human-readable representation of the payload.

        """
        return f"{_label(sm.events, 'msg', self.identifier)} · data_len={self.data_len} · value={self.value:#010x}"


class SMALDebugDataPayload(BaseModel):
    """Payload for data read/write debug entries."""

    entry_type: Literal["data"] = Field(default="data", exclude=True)
    address: UInt32 = Field(description="Address that was read from or written to.")
    data_len: UInt32 = Field(description="Length of data that was read or written, in bytes.")

    def display(self, sm: Machine) -> str:  # noqa: ARG002 - unused method argument
        """Return a human-readable representation of this payload.

        Args:
            sm (Machine): The state machine to resolve against.

        Returns:
            str: Human-readable representation of the payload.

        """
        return f"address={self.address:#010x} · data_len={self.data_len}"


class SMALDebugErrorPayload(BaseModel):
    """Payload for error debug entries."""

    entry_type: Literal["error"] = Field(default="error", exclude=True)
    error_code: Int32 = Field(description="Error code (negative for error types, non-negative for specific codes).")
    detail: UInt32 = Field(description="Additional error detail (address, value, bitmask, etc.).")

    def display(self, sm: Machine) -> str:
        """Return a human-readable representation of this payload.

        Args:
            sm (Machine): The state machine to resolve against.

        Returns:
            str: Human-readable representation of the payload.

        """
        return f"{_label(sm.errors, 'error', self.error_code)} · detail={self.detail:#010x}"


# Rendered in each target language as a tagged union (see TaggedUnionSpec)
SMALDebugPayload = Annotated[
    SMALDebugTransitionPayload | SMALDebugMessagePayload | SMALDebugDataPayload | SMALDebugErrorPayload,
    Field(discriminator="entry_type"),
]


class SMALDebugEntry(BaseModel):
    """Debug entry structure representing a single debug log entry."""

    entry_type: UInt32 = Field(description="Bitmask indicating the type of entry (state transition, event, command, data read/write, error, etc.).")
    timestamp_ms: UInt32 = Field(description="Timestamp in milliseconds when the entry was logged.")
    payload: Annotated[SMALDebugPayload, RefTo("dbg_payload")] = Field(description="The payload of the entry, interpreted based on entry_type.")

    @staticmethod
    def deserialize_entries_from_bytes(data: bytearray, endianness: Literal["little", "big"] = "little") -> list[SMALDebugEntry]:
        """Deserialize a bytearray containing binary debug entries into a list of SMALDebugEntry objects.

        Every entry is a header (its directly-encoded fields, in order) followed by a payload sized for the largest payload type.
        The header and payload layouts are derived from the models' field types, so adding a field changes the wire format with no other edit.

        Args:
            data: Bytearray containing serialized debug entries.
            endianness: Byte order used to deserialize entries ("little" or "big").

        Returns:
            List of SMALDebugEntry objects ordered by occurrence in the data.

        Raises:
            ValueError: If data length is not a multiple of the size in bytes of an entry.

        """
        prefix = "<" if endianness == "little" else ">"
        header, header_fields = _layout(StructSpec.build(SMALDebugEntry, "dbg_entry"), prefix)
        layouts = {model: _payload_layout(model, prefix) for _, _, model in _PAYLOADS}
        entry_size = header.size + max(layout.size for layout, _ in layouts.values())
        if len(data) % entry_size != 0:
            raise ValueError(f"Invalid debug data size: {len(data)} bytes is not a multiple of {entry_size} bytes")
        entries: list[SMALDebugEntry] = []
        for offset in range(0, len(data), entry_size):
            header_values = dict(zip(header_fields, header.unpack_from(data, offset), strict=True))
            model = _payload_model(header_values["entry_type"])
            layout, field_names = layouts[model]
            payload = model(**dict(zip(field_names, layout.unpack_from(data, offset + header.size), strict=True)))
            entries.append(SMALDebugEntry(**header_values, payload=payload))
        return entries


class SMALDebugRing(BaseModel):
    """Debug ring buffer structure for storing debug entries."""

    oldest_index: UInt16 = Field(description="Index of the oldest entry in the ring buffer.")
    write_index: UInt16 = Field(description="Index where the next entry will be written.")
    entry_count: UInt16 = Field(description="Number of valid entries currently in the ring.")
    capacity: UInt16 = Field(description="Maximum number of entries the ring can hold.")
    overwrite_count: UInt16 = Field(description="Number of times entries have been overwritten.")
    entries: Annotated[list[SMALDebugEntry], RefTo("dbg_entry", array=True, count_field="capacity")] = Field(
        description="Array of debug entries in the ring buffer.",
    )


class SMALFlushStatus(BaseModel):
    """Model defining flush parameters for transmitting debug data out of the ring buffer."""

    active: Bool = Field(default=False, description="Indicates whether a flush cycle is currently active.")
    entry_transmit_complete: Bool = Field(
        default=False,
        description="Indicates whether the entry transmission for the current flush cycle is complete.",
    )
    oldest_idx: UInt16 = Field(default=0, description="The index of the oldest entry in the ring at the start of the flush cycle.")
    entry_count: UInt16 = Field(
        default=0,
        description=(
            "The total number of entries that need to be sent in the current flush cycle, "
            "i.e. the number of entries that were in the ring at the start of the flush."
        ),
    )
    num_entries_sent: UInt16 = Field(default=0, description="The number of entries that have been sent so far in the current flush cycle.")


# Each payload's logical struct name, the entry types that select it, and its model. Checked in order, and the first one whose mask
# overlaps the entry type wins. Names are the C names without the `smal_` prefix and `_t` suffix, so the C output stays unchanged.
_PAYLOADS: Final[tuple[tuple[str, SMALDebugEntryType, type[BaseModel]], ...]] = (
    ("dbg_transition_payload", SMALDebugEntryType.ENTRY_TYPE_STATE_TRANSITION, SMALDebugTransitionPayload),
    ("dbg_error_payload", SMALDebugEntryType.ENTRY_TYPE_ERROR, SMALDebugErrorPayload),
    (
        "dbg_message_payload",
        SMALDebugEntryType.ENTRY_TYPE_EVENT_RX
        | SMALDebugEntryType.ENTRY_TYPE_EVENT_TX
        | SMALDebugEntryType.ENTRY_TYPE_CMD_RX
        | SMALDebugEntryType.ENTRY_TYPE_CMD_TX,
        SMALDebugMessagePayload,
    ),
    ("dbg_data_payload", SMALDebugEntryType.ENTRY_TYPE_DATA_READ | SMALDebugEntryType.ENTRY_TYPE_DATA_WRITE, SMALDebugDataPayload),
)


def _payload_model(entry_type: int) -> type[BaseModel]:
    """Get the payload model selected by an entry type bitmask, defaulting to the transition payload.

    Args:
        entry_type (int): The entry type bitmask.

    Returns:
        type[BaseModel]: The payload model.

    """
    return next((model for _, mask, model in _PAYLOADS if entry_type & mask), SMALDebugTransitionPayload)


def _struct_code(wire: WireType) -> str:
    """Get the `struct` format code of a wire type.

    Args:
        wire (WireType): The wire type.

    Raises:
        ValueError: If the wire type has no format code (for example an enum, whose storage type isn't carried by the field).

    Returns:
        str: The format code.

    """
    if wire.primitive == SMALPrimitive.BYTES:
        return f"{wire.length}s"
    code = wire.primitive.struct_code
    if code is None:
        raise ValueError(f"{wire.primitive.value} has no struct format code.")
    return code


def _layout(spec: StructSpec, prefix: str) -> tuple[struct.Struct, tuple[str, ...]]:
    """Get the struct format and field names for the directly-encoded fields of a struct, skipping references to other types.

    Args:
        spec (StructSpec): The struct to lay out.
        prefix (str): The `struct` byte order prefix, e.g. "<" for packed little-endian.

    Returns:
        tuple[struct.Struct, tuple[str, ...]]: The compiled struct and the names of its fields, in order.

    """
    wire_fields = [f for f in spec.fields if f.wire is not None]
    return struct.Struct(prefix + "".join(_struct_code(f.wire) for f in wire_fields)), tuple(f.name for f in wire_fields)


def _payload_layout(model: type[BaseModel], prefix: str) -> tuple[struct.Struct, tuple[str, ...]]:
    """Get the struct format and field names of a payload model.

    Args:
        model (type[BaseModel]): The payload model.
        prefix (str): The `struct` byte order prefix.

    Returns:
        tuple[struct.Struct, tuple[str, ...]]: The compiled struct and the names of its fields, in order.

    """
    return _layout(StructSpec.build(model, model.__name__), prefix)


@dataclass(frozen=True)
class FieldSpec:
    """A field of a struct, described without reference to any target language."""

    name: str
    wire: WireType | None  # None when the field refers to another type
    ref: str | None  # The logical name of the struct or union this field refers to
    description: str
    array: bool = False  # A runtime-sized array of `ref`
    count_field: str | None = None  # For arrays: the sibling field holding the number of elements

    def __post_init__(self) -> None:
        """Validate the construction of FieldSpec.

        Raises:
            ValueError: If not exactly one of wire and ref is set.
            ValueError: If array or count_field is used on a field that isn't a reference.
            ValueError: If count_field is used on a field that isn't an array.

        """
        has_wire, has_ref = self.wire is not None, bool(self.ref)
        if has_wire == has_ref:
            raise ValueError(f"Field '{self.name}' must set exactly one of wire or ref.")
        if (self.array or self.count_field) and not has_ref:
            raise ValueError(f"Field '{self.name}': array and count_field are only valid for references.")
        if self.count_field and not self.array:
            raise ValueError(f"Field '{self.name}': count_field is only valid for arrays.")


@dataclass(frozen=True)
class StructSpec:
    """A struct, described without reference to any target language."""

    name: str
    fields: tuple[FieldSpec, ...]
    packed: bool = True

    def __post_init__(self) -> None:
        """Validate the construction of StructSpec.

        Raises:
            ValueError: If two fields share a name.
            ValueError: If an array's count_field is not a directly-encoded field of this struct.

        """
        names = [f.name for f in self.fields]
        if len(set(names)) != len(names):
            raise ValueError(f"Struct '{self.name}' has duplicate field names.")
        plain_fields = {f.name for f in self.fields if f.wire is not None}
        for f in self.fields:
            if f.count_field is not None and f.count_field not in plain_fields:
                raise ValueError(f"Struct '{self.name}': field '{f.name}' counts by '{f.count_field}', which is not a plain field of the struct.")

    @classmethod
    def build(cls, model: type[BaseModel], name: str, *, packed: bool = True) -> StructSpec:
        """Build a StructSpec from a pydantic model whose fields are annotated with a WireType or a RefTo.

        Fields with `exclude=True` (such as a payload's discriminator) are not part of the wire layout and are skipped.

        Args:
            model (type[BaseModel]): The model to describe.
            name (str): The logical name of the struct.
            packed (bool, optional): Whether the struct is packed. Defaults to True.

        Raises:
            RuntimeError: If a field has neither or both of WireType and RefTo.

        Returns:
            StructSpec: The struct description.

        """
        fields = []
        for field_name, info in model.model_fields.items():
            if info.exclude:
                continue
            wire = next((m for m in info.metadata if isinstance(m, WireType)), None)
            ref = next((m for m in info.metadata if isinstance(m, RefTo)), None)
            if (wire is None) == (ref is None):
                raise RuntimeError(f"{model.__name__}.{field_name} must have exactly one of WireType or RefTo. This is a programming error.")
            fields.append(
                FieldSpec(
                    name=field_name,
                    wire=wire,
                    ref=ref.name if ref else None,
                    description=info.description or "",
                    array=ref.array if ref else False,
                    count_field=ref.count_field if ref else None,
                ),
            )
        return cls(name=name, fields=tuple(fields), packed=packed)


@dataclass(frozen=True)
class EnumSpec:
    """An enum, described without reference to any target language."""

    name: str
    storage: SMALPrimitive
    members: tuple[tuple[str, int], ...]  # (member name, value), in definition order
    flags: bool = False
    prefix: str = ""  # Namespaces the members in the target language, in lower snake case, e.g. "dbg"
    include_count: bool = True
    include_null: bool = True

    @classmethod
    def build(
        cls,
        enum: type[Enum],
        name: str,
        storage: SMALPrimitive = SMALPrimitive.UINT32,
        flags: bool | None = None,
        prefix: str = "",
        include_count: bool = True,
        include_null: bool = True,
    ) -> EnumSpec:
        """Build an EnumSpec from a python enum.

        Zero-valued members and aliases are included (iterating a Flag would skip them).

        Args:
            enum (type[Enum]): The python enum.
            name (str): The logical name of the enum.
            storage (SMALPrimitive, optional): The integer type that stores it. Defaults to UINT32.
            flags (bool | None, optional): Whether the members are bit flags. Defaults to whether `enum` is a Flag.
            prefix (str, optional): Namespace prefix for the members in the target language. Defaults to none.
            include_count (bool, optional): Include a count member. Defaults to True.
            include_null (bool, optional): Include a null member. Defaults to True.

        Raises:
            ValueError: If storage is not an integer type, or a member's value doesn't fit it.

        Returns:
            EnumSpec: The enum description.

        """
        if not storage.is_integer:
            raise ValueError(f"Enum '{enum.__name__}' storage must be an integer type, not '{storage.value}'.")
        members = tuple((member_name, member.value) for member_name, member in enum.__members__.items())
        # TODO: Check members for anything that could collide with count and null
        for member_name, value in members:
            try:
                storage.check_value(value)
            except ValueError as exc:
                raise ValueError(f"Enum '{enum.__name__}' member '{member_name}' does not fit {storage.value}: {exc}") from exc
        return cls(
            name=name,
            storage=storage,
            members=members,
            flags=issubclass(enum, Flag) if flags is None else flags,
            prefix=prefix,
            include_count=include_count,
            include_null=include_null,
        )

    @classmethod
    def build_from_data(
        cls,
        data: dict[str, int],
        name: str,
        storage: SMALPrimitive = SMALPrimitive.UINT32,
        flags: bool | None = None,
        prefix: str = "",
        include_count: bool = True,
        include_null: bool = True,
    ) -> EnumSpec:
        """Build an EnumSpec from dynamic data instead of a pre-defined python Enum.

        Args:
            data (dict[str, int]): The enum members and their values.
            name (str): The enum name.
            storage (SMALPrimitive, optional): The storage type. Defaults to SMALPrimitive.UINT32.
            flags (bool | None, optional): Whether it's a flag enum. Defaults to None.
            prefix (str, optional): Prefix for members. Defaults to "".
            include_count (bool, optional): Include count member. Defaults to True.
            include_null (bool, optional): Include null member. Defaults to True.

        Returns:
            EnumSpec: The enum spec.

        """
        dynamic_enum = Enum(name, data)
        return cls.build(dynamic_enum, name, storage, flags, prefix, include_count, include_null)


@dataclass(frozen=True)
class TaggedUnionSpec:
    """A union whose active variant is chosen by a tag, described without reference to any target language."""

    name: str
    tag: str
    variants: tuple[tuple[str, str], ...]  # (tag value, struct name)

    @classmethod
    def from_models(cls, name: str, tag: str, models: Iterable[tuple[str, type[BaseModel]]]) -> TaggedUnionSpec:
        """Build a TaggedUnionSpec from the models that are its variants.

        Each model's `tag` field must be a Literal with a default, which becomes that variant's tag value.

        Args:
            name (str): The logical name of the union.
            tag (str): The name of the discriminator field on every model.
            models (Iterable[tuple[str, type[BaseModel]]]): Each variant's logical struct name and model.

        Raises:
            TypeError: If a model has no string default for the tag field.
            ValueError: If two variants share a tag value.

        Returns:
            TaggedUnionSpec: The union description.

        """
        variants = []
        for struct_name, model in models:
            tag_value = model.model_fields[tag].default
            if not isinstance(tag_value, str):
                raise TypeError(f"{model.__name__}.{tag} must be a Literal with a string default.")
            variants.append((tag_value, struct_name))
        tag_values = [v for v, _ in variants]
        duplicates = sorted({v for v in tag_values if tag_values.count(v) > 1})
        if duplicates:
            raise ValueError(f"Union '{name}' has variants sharing the tag values {duplicates}.")
        return cls(name=name, tag=tag, variants=tuple(variants))


def _dependencies(item: EnumSpec | StructSpec | TaggedUnionSpec) -> list[str]:
    """Get the names of the types that must be defined before `item`, in a stable order.

    Args:
        item (EnumSpec | StructSpec | TaggedUnionSpec): The type to inspect.

    Returns:
        list[str]: The names of the types it depends on.

    """
    if isinstance(item, StructSpec):
        deps = []
        for f in item.fields:
            if f.ref:
                deps.append(f.ref)
            elif f.wire is not None and f.wire.enum_name:
                deps.append(f.wire.enum_name)
        return deps
    if isinstance(item, TaggedUnionSpec):
        return [struct_name for _, struct_name in item.variants]
    return []


@dataclass(frozen=True)
class DebugCodegenContext:
    """Everything a target language needs to generate the debug types, with no language-specific content."""

    enums: tuple[EnumSpec, ...]
    structs: tuple[StructSpec, ...]
    unions: tuple[TaggedUnionSpec, ...]

    def __post_init__(self) -> None:
        """Validate the context by computing the definition order, which checks names and references."""
        self._ordered()

    @classmethod
    def build(cls, *_args: Any, **_kwargs: Any) -> DebugCodegenContext:
        """Build the context for the SMAL debug types.

        Returns:
            DebugCodegenContext: The context.

        """
        return cls(
            enums=(EnumSpec.build(SMALDebugEntryType, "dbg_entry_type", prefix="dbg"),),
            structs=(
                *(StructSpec.build(model, name, packed=False) for name, _, model in _PAYLOADS),
                StructSpec.build(SMALDebugEntry, "dbg_entry", packed=False),
                StructSpec.build(SMALDebugRing, "dbg_ring", packed=False),
                StructSpec.build(SMALFlushStatus, "dbg_flush_status", packed=False),
            ),
            unions=(TaggedUnionSpec.from_models("dbg_payload", "entry_type", ((name, model) for name, _, model in _PAYLOADS)),),
        )

    def _ordered(self) -> list[tuple[str, Any]]:
        """Order every type so each comes after the types it depends on.

        Raises:
            ValueError: If two types share a name, a type refers to one that doesn't exist, or the references form a cycle.

        Returns:
            list[tuple[str, Any]]: (kind, spec) pairs, where kind is "enum", "struct" or "union". Ties keep the declared order.

        """
        items: dict[str, tuple[str, Any]] = {}
        for kind, group in (("enum", self.enums), ("struct", self.structs), ("union", self.unions)):
            for item in group:
                if item.name in items:
                    raise ValueError(f"Duplicate type name '{item.name}' among enums, structs and unions.")
                items[item.name] = (kind, item)
        ordered: list[tuple[str, Any]] = []
        done: set[str] = set()
        visiting: list[str] = []

        def visit(name: str) -> None:
            if name in done:
                return
            if name in visiting:
                raise ValueError(f"Circular type dependency: {' -> '.join([*visiting[visiting.index(name) :], name])}")
            visiting.append(name)
            kind, item = items[name]
            for dep in _dependencies(item):
                if dep not in items:
                    raise ValueError(f"'{name}' refers to unknown type '{dep}'.")
                visit(dep)
            visiting.pop()
            done.add(name)
            ordered.append((kind, item))

        for name in items:
            visit(name)
        return ordered

    @property
    def all_data(self) -> list[tuple[str, Any]]:
        """Get every type as a (kind, spec) pair, in dependency order.

        Returns:
            list[tuple[str, Any]]: The types, each after the types it depends on.

        """
        return self._ordered()
