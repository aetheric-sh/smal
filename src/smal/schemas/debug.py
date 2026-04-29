"""Module defining the schema for the debug structures for SMAL state machines."""

from __future__ import annotations  # Until Python 3.14

import struct
from dataclasses import dataclass
from enum import Enum, IntFlag
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Final, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Self

if TYPE_CHECKING:
    from smal.schemas.state_machine import StateMachine

METADATA_C_DATATYPE: Final[str] = "c_datatype"
METADATA_C_PACKED: Final[str] = "packed"


@dataclass(frozen=True)
class CStructData:
    """Dataclass representing the data necessary to construct a C Struct."""

    struct_name: str
    fields: dict[str, tuple[str, str]]
    packed: bool = False

    @classmethod
    def from_model(cls, model: type[BaseModel]) -> Self:
        """Construct a CStructData from an arbitrary pydantic BaseModel.

        Args:
            model (type[BaseModel]): The pydantic BaseModel.

        Raises:
            RuntimeError: If the model does not define metadata for its C datatype.
            RuntimeError: If any field within the model does not define metadata for its C datatype.

        Returns:
            Self: The constructed CStructData.

        """
        cls_metadata = model.model_config.get("json_schema_extra", {})
        struct_name = cls_metadata.get(METADATA_C_DATATYPE, None)
        if struct_name is None:
            raise RuntimeError(f"Model '{model.__name__}' does not define a C struct name. This is a programming error.")
        fields: dict[str, tuple[str, str]] = {}
        for field_name, field_info in model.model_fields.items():
            if field_info.exclude:
                continue
            if field_info.json_schema_extra is None:
                raise RuntimeError("No json_schema_extra for Field. This is a programming error.")
            dtype = field_info.json_schema_extra.get(METADATA_C_DATATYPE, None)
            if dtype is None:
                raise RuntimeError("Field does not define a C datatype. This is a programming error.")
            fields[field_name] = (dtype, field_info.description or "")
        packed = cls_metadata.get(METADATA_C_PACKED, False)
        return cls(
            struct_name=struct_name,
            fields=fields,
            packed=packed,
        )


CUnionData: TypeAlias = CStructData


@dataclass(frozen=True)
class CEnumData:
    """Dataclass representing the data necessary to construct a C Enum."""

    name: str
    values: dict[str, Any]

    @classmethod
    def from_py_enum(cls, e: type[Enum]) -> Self:
        """Construct a CEnumData from an arbitrary python enum, if applicable.

        Args:
            e (type[Enum]): The python enum.

        Raises:
            RuntimeError: If the given enum does not expose a method to get the C datatype.

        Returns:
            Self: The constructed CEnumData.

        """
        if not hasattr(e, METADATA_C_DATATYPE):
            raise RuntimeError(f"Enumeration type '{e.__name__}' does not expose {METADATA_C_DATATYPE} property")
        return cls(
            name=e.c_datatype(),
            values={f"SMAL_DBG_{en.name.upper()}": en.value for en in e},
        )


@dataclass(frozen=True)
class CCodegenContext:
    """Jinja2 codegen context for C data."""

    enums: list[CEnumData]
    structs: list[CStructData]
    unions: list[CUnionData]
    definition_order: list[str] | None = None

    @property
    def all_data(self) -> list[tuple[str, Any]]:
        """Get all C data in a single list, ordered by definition order if provided."""
        if self.definition_order is None:
            enums = [("enum", e) for e in self.enums]
            structs = [("struct", s) for s in self.structs]
            unions = [("union", u) for u in self.unions]
            return enums + structs + unions
        retval: list[tuple[str, Any]] = []
        for name in self.definition_order:
            item = next((e for e in self.enums if name == e.name), None)
            if item is not None:
                retval.append(("enum", item))
                continue
            item = next((s for s in self.structs if name == s.struct_name), None)
            if item is not None:
                retval.append(("struct", item))
                continue
            item = next((u for u in self.unions if name == u.struct_name), None)
            if item is not None:
                retval.append(("union", item))
                continue
        return retval


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

    @staticmethod
    def c_datatype() -> str:
        """Get the C datatype of this python enum.

        Returns:
            str: The C datatype of this python enum.

        """
        return "smal_dbg_entry_type_t"


class SMALDebugTransitionPayload(BaseModel):
    """Payload for state transition debug entries."""

    C_DATATYPE: ClassVar[str] = "smal_dbg_transition_payload_t"

    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra={METADATA_C_DATATYPE: C_DATATYPE, METADATA_C_PACKED: False},
    )

    entry_type: Literal["transition"] = Field(default="transition", exclude=True)
    src_state: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Source state ID or index before the transition.",
        json_schema_extra={METADATA_C_DATATYPE: "uint16_t"},
    )
    tgt_state: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Target state ID or index after the transition.",
        json_schema_extra={METADATA_C_DATATYPE: "uint16_t"},
    )
    evt: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Event ID or index that triggered the transition.",
        json_schema_extra={METADATA_C_DATATYPE: "uint16_t"},
    )
    status: int = Field(
        ...,
        ge=-32768,
        le=32767,
        description="Status of the transition (success, failure, error code, etc.).",
        json_schema_extra={METADATA_C_DATATYPE: "int16_t"},
    )

    def display(self, sm: StateMachine) -> str:
        """Return a human-readable representation of this payload.

        Args:
            sm (StateMachine): The state machine to resolve against.

        Returns:
            str: Human-readable representation of the payload.

        """

        def resolve_state_name(state_id: int) -> str:
            for idx, state in enumerate(sm.states):
                candidate_id = state.id if state.id is not None else idx
                if candidate_id == state_id:
                    return state.name
            return f"state#{state_id}"

        def resolve_event_name(event_id: int) -> str:
            for idx, event in enumerate(sm.events):
                candidate_id = event.id if event.id is not None else idx
                if candidate_id == event_id:
                    return event.name
            return f"event#{event_id}"

        def resolve_error_name(error_code: int) -> str:
            for idx, error in enumerate(sm.errors):
                candidate_id = error.id if error.id is not None else idx
                if candidate_id == error_code:
                    return error.name
            return f"error#{error_code}"

        src_name = resolve_state_name(self.src_state)
        tgt_name = resolve_state_name(self.tgt_state)
        evt_name = resolve_event_name(self.evt)
        error_name = resolve_error_name(self.status) if self.status != 0 else "OK"
        return f"{src_name}({self.src_state}) --[{evt_name}({self.evt})]--> {tgt_name}({self.tgt_state}) · {error_name}({self.status})"


class SMALDebugMessagePayload(BaseModel):
    """Payload for event/command debug entries."""

    C_DATATYPE: ClassVar[str] = "smal_dbg_message_payload_t"

    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra={METADATA_C_DATATYPE: C_DATATYPE, METADATA_C_PACKED: False},
    )

    entry_type: Literal["message"] = Field(default="message", exclude=True)
    identifier: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Event or command ID/index.",
        json_schema_extra={METADATA_C_DATATYPE: "uint16_t"},
    )
    data_len: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Length of data associated with the event or command, in bytes.",
        json_schema_extra={METADATA_C_DATATYPE: "uint16_t"},
    )
    value: int = Field(
        ...,
        ge=0,
        le=0xFFFFFFFF,
        description="Value associated with the event or command (parameter, status code, etc.).",
        json_schema_extra={METADATA_C_DATATYPE: "uint32_t"},
    )

    def display(self, sm: StateMachine) -> str:
        """Return a human-readable representation of this payload.

        Args:
            sm (StateMachine): The state machine to resolve against.

        Returns:
            str: Human-readable representation of the payload.

        """

        def resolve_command_name(command_id: int) -> str:
            for idx, command in enumerate(sm.commands):
                candidate_id = command.id if command.id is not None else idx
                if candidate_id == command_id:
                    return command.name
            raise ValueError(f"Command ID {command_id} not found in state machine commands.")

        def resolve_event_name(event_id: int) -> str:
            for idx, event in enumerate(sm.events):
                candidate_id = event.id if event.id is not None else idx
                if candidate_id == event_id:
                    return event.name
            raise ValueError(f"Event ID {event_id} not found in state machine events.")

        def resolve_message_name(identifier: int) -> str:
            try:
                return resolve_command_name(identifier)
            except ValueError:
                try:
                    return resolve_event_name(identifier)
                except ValueError:
                    return f"msg#{identifier}"

        msg_name = resolve_message_name(self.identifier)
        return f"{msg_name}({self.identifier}) · data_len={self.data_len} · value={self.value:#010x}"


class SMALDebugDataPayload(BaseModel):
    """Payload for data read/write debug entries."""

    C_DATATYPE: ClassVar[str] = "smal_dbg_data_payload_t"

    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra={METADATA_C_DATATYPE: C_DATATYPE, METADATA_C_PACKED: False},
    )

    entry_type: Literal["data"] = Field(default="data", exclude=True)
    address: int = Field(
        ...,
        ge=0,
        le=0xFFFFFFFF,
        description="Address that was read from or written to.",
        json_schema_extra={METADATA_C_DATATYPE: "uint32_t"},
    )
    data_len: int = Field(
        ...,
        ge=0,
        le=0xFFFFFFFF,
        description="Length of data that was read or written, in bytes.",
        json_schema_extra={METADATA_C_DATATYPE: "uint32_t"},
    )

    def display(self, sm: StateMachine) -> str:  # noqa: ARG002 - unused method argument
        """Return a human-readable representation of this payload.

        Args:
            sm (StateMachine): The state machine to resolve against.


        Returns:
            str: Human-readable representation of the payload.

        """
        return f"address={self.address:#010x} · data_len={self.data_len}"


class SMALDebugErrorPayload(BaseModel):
    """Payload for error debug entries."""

    C_DATATYPE: ClassVar[str] = "smal_dbg_error_payload_t"

    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra={METADATA_C_DATATYPE: C_DATATYPE, METADATA_C_PACKED: False},
    )

    entry_type: Literal["error"] = Field(default="error", exclude=True)
    error_code: int = Field(
        ...,
        ge=-2147483648,
        le=2147483647,
        description="Error code (negative for error types, non-negative for specific codes).",
        json_schema_extra={METADATA_C_DATATYPE: "int32_t"},
    )
    detail: int = Field(
        ...,
        ge=0,
        le=0xFFFFFFFF,
        description="Additional error detail (address, value, bitmask, etc.).",
        json_schema_extra={METADATA_C_DATATYPE: "uint32_t"},
    )

    def display(self, sm: StateMachine) -> str:
        """Return a human-readable representation of this payload.

        Args:
            sm (StateMachine): The state machine to resolve against.

        Returns:
            str: Human-readable representation of the payload.

        """

        def resolve_error_name(error_code: int) -> str:
            for idx, error in enumerate(sm.errors):
                candidate_id = error.id if error.id is not None else idx
                if candidate_id == error_code:
                    return error.name
            return f"error#{error_code}"

        err_name = resolve_error_name(self.error_code)
        return f"{err_name}({self.error_code}) · detail={self.detail:#010x}"


# TODO: Figure out how to make this into a union in c code
SMALDebugPayload = Annotated[
    SMALDebugTransitionPayload | SMALDebugMessagePayload | SMALDebugDataPayload | SMALDebugErrorPayload,
    Field(discriminator="entry_type"),
]


class SMALDebugEntry(BaseModel):
    """Debug entry structure representing a single debug log entry."""

    C_DATATYPE: ClassVar[str] = "smal_dbg_entry_t"

    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra={METADATA_C_DATATYPE: C_DATATYPE, METADATA_C_PACKED: False},
    )

    entry_type: int = Field(
        ...,
        ge=0,
        le=0xFFFFFFFF,
        description="Bitmask indicating the type of entry (state transition, event, command, data read/write, error, etc.).",
        json_schema_extra={METADATA_C_DATATYPE: "uint32_t"},
    )
    timestamp_ms: int = Field(
        ...,
        ge=0,
        le=0xFFFFFFFF,
        description="Timestamp in milliseconds when the entry was logged.",
        json_schema_extra={METADATA_C_DATATYPE: "uint32_t"},
    )
    payload: SMALDebugPayload = Field(
        ...,
        description="The payload of the entry, interpreted based on entry_type.",
        json_schema_extra={METADATA_C_DATATYPE: "smal_dbg_payload_t"},
    )

    @staticmethod
    def deserialize_entries_from_bytes(data: bytearray, endianness: Literal["little", "big"] = "little") -> list[SMALDebugEntry]:
        """Deserialize a bytearray containing binary smal_dbg_entry_t structures into a list of SMALDebugEntry objects.

        The bytearray should contain a series of debug entries, each consisting of:
        - entry_type (uint32, 4 bytes): Bitmask indicating the type of entry
        - timestamp_ms (uint32, 4 bytes): Timestamp when the entry was logged
        - payload (8 bytes): Union of various payload types interpreted by entry_type

        Payload format for STATE_TRANSITION entries:
        - src_state (uint16): Source state ID/index before transition
        - tgt_state (uint16): Target state ID/index after transition
        - evt (uint16): Event ID/index that triggered the transition
        - status (int16): Status of the transition

        Args:
            data: Bytearray containing serialized debug entries.
            endianness: Byte order used to deserialize entries ("little" or "big").

        Returns:
            List of SMALDebugEntry objects ordered by occurrence in the data.

        Raises:
            ValueError: If data length is not a multiple of the size in bytes of SMALDebugEntry or payload unpacking fails.

        """
        endian_prefix = "<" if endianness == "little" else ">"
        header_fmt = f"{endian_prefix}II"
        transition_fmt = f"{endian_prefix}HHHh"
        error_fmt = f"{endian_prefix}iI"
        message_fmt = f"{endian_prefix}HHI"
        data_fmt = f"{endian_prefix}II"
        header_size_bytes = struct.calcsize(header_fmt)
        payload_size_bytes = max(
            struct.calcsize(transition_fmt),
            struct.calcsize(error_fmt),
            struct.calcsize(message_fmt),
            struct.calcsize(data_fmt),
        )
        entry_size_bytes = header_size_bytes + payload_size_bytes
        if len(data) % entry_size_bytes != 0:
            raise ValueError(f"Invalid debug data size: {len(data)} bytes is not a multiple of {entry_size_bytes} bytes")
        entries: list[SMALDebugEntry] = []
        for i in range(0, len(data), entry_size_bytes):
            chunk = data[i : i + entry_size_bytes]
            # Unpack header: entry_type (uint32) | timestamp_ms (uint32)
            entry_type, timestamp_ms = struct.unpack(header_fmt, chunk[0:header_size_bytes])
            payload_bytes = chunk[header_size_bytes : header_size_bytes + payload_size_bytes]
            # Determine payload type based on entry_type bitmask and parse accordingly
            payload_dict: dict = {"entry_type": _get_payload_type(entry_type)}
            if entry_type & SMALDebugEntryType.ENTRY_TYPE_STATE_TRANSITION:
                # Unpack payload: src_state (u16) | tgt_state (u16) | evt (u16) | status (i16)
                src_state, tgt_state, evt, status = struct.unpack(transition_fmt, payload_bytes[0:payload_size_bytes])
                payload_dict.update(
                    {
                        "src_state": src_state,
                        "tgt_state": tgt_state,
                        "evt": evt,
                        "status": status,
                    },
                )
            elif entry_type & SMALDebugEntryType.ENTRY_TYPE_ERROR:
                error_code, detail = struct.unpack(error_fmt, payload_bytes[0:payload_size_bytes])
                payload_dict.update({"error_code": error_code, "detail": detail})
            elif entry_type & (
                SMALDebugEntryType.ENTRY_TYPE_EVENT_RX | SMALDebugEntryType.ENTRY_TYPE_EVENT_TX | SMALDebugEntryType.ENTRY_TYPE_CMD_RX | SMALDebugEntryType.ENTRY_TYPE_CMD_TX
            ):
                identifier, data_len, value = struct.unpack(message_fmt, payload_bytes[0:payload_size_bytes])
                payload_dict.update(
                    {
                        "identifier": identifier,
                        "data_len": data_len,
                        "value": value,
                    },
                )
            elif entry_type & (SMALDebugEntryType.ENTRY_TYPE_DATA_READ | SMALDebugEntryType.ENTRY_TYPE_DATA_WRITE):
                address, data_len = struct.unpack(data_fmt, payload_bytes[0:payload_size_bytes])
                payload_dict.update({"address": address, "data_len": data_len})
            else:
                # Default to transition payload if no specific type matched
                src_state, tgt_state, evt, status = struct.unpack(transition_fmt, payload_bytes[0:payload_size_bytes])
                payload_dict.update(
                    {
                        "src_state": src_state,
                        "tgt_state": tgt_state,
                        "evt": evt,
                        "status": status,
                    },
                )
            entry = SMALDebugEntry(entry_type=entry_type, timestamp_ms=timestamp_ms, payload=payload_dict)
            entries.append(entry)
        return entries


class SMALDebugRing(BaseModel):
    """Debug ring buffer structure for storing debug entries."""

    C_DATATYPE: ClassVar[str] = "smal_dbg_ring_t"

    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra={METADATA_C_DATATYPE: C_DATATYPE, METADATA_C_PACKED: False},
    )

    oldest_index: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Index of the oldest entry in the ring buffer.",
        json_schema_extra={METADATA_C_DATATYPE: "uint16_t"},
    )
    write_index: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Index where the next entry will be written.",
        json_schema_extra={METADATA_C_DATATYPE: "uint16_t"},
    )
    entry_count: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Number of valid entries currently in the ring.",
        json_schema_extra={METADATA_C_DATATYPE: "uint16_t"},
    )
    capacity: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Maximum number of entries the ring can hold.",
        json_schema_extra={METADATA_C_DATATYPE: "uint16_t"},
    )
    overwrite_count: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Number of times entries have been overwritten.",
        json_schema_extra={METADATA_C_DATATYPE: "uint16_t"},
    )
    entries: list[SMALDebugEntry] = Field(
        ...,
        description="Array of debug entries in the ring buffer.",
        json_schema_extra={METADATA_C_DATATYPE: f"{SMALDebugEntry.C_DATATYPE} *"},
    )


class SMALFlushStatus(BaseModel):
    """Model defining flush parameters for transmitting debug data out of the ring buffer."""

    C_DATATYPE: ClassVar[str] = "smal_dbg_flush_status_t"

    model_config: ClassVar[ConfigDict] = ConfigDict(
        json_schema_extra={METADATA_C_DATATYPE: C_DATATYPE, METADATA_C_PACKED: False},
    )

    active: bool = Field(
        default=False,
        description="Indicates whether a flush cycle is currently active.",
        json_schema_extra={METADATA_C_DATATYPE: "bool"},
    )
    entry_transmit_complete: bool = Field(
        default=False,
        description="Indicates whether the entry transmission for the current flush cycle is complete.",
        json_schema_extra={METADATA_C_DATATYPE: "bool"},
    )
    oldest_idx: int = Field(
        default=0,
        ge=0,
        le=0xFFFF,
        description="The index of the oldest entry in the ring at the start of the flush cycle.",
        json_schema_extra={METADATA_C_DATATYPE: "uint16_t"},
    )
    entry_count: int = Field(
        default=0,
        ge=0,
        le=0xFFFF,
        description="The total number of entries that need to be sent in the current flush cycle, i.e. the number of entries that were in the ring at the start of the flush.",
        json_schema_extra={METADATA_C_DATATYPE: "uint16_t"},
    )
    num_entries_sent: int = Field(
        default=0,
        ge=0,
        le=0xFFFF,
        description="The number of entries that have been sent so far in the current flush cycle.",
        json_schema_extra={METADATA_C_DATATYPE: "uint16_t"},
    )


def _get_payload_type(entry_type: int) -> str:
    """Determine the payload type discriminator based on entry_type bitmask.

    Args:
        entry_type: The entry_type bitmask from the debug entry.

    Returns:
        The discriminator string for the payload type.

    """
    if entry_type & SMALDebugEntryType.ENTRY_TYPE_STATE_TRANSITION:
        return "transition"
    if entry_type & SMALDebugEntryType.ENTRY_TYPE_ERROR:
        return "error"
    if entry_type & (SMALDebugEntryType.ENTRY_TYPE_EVENT_RX | SMALDebugEntryType.ENTRY_TYPE_EVENT_TX | SMALDebugEntryType.ENTRY_TYPE_CMD_RX | SMALDebugEntryType.ENTRY_TYPE_CMD_TX):
        return "message"
    if entry_type & (SMALDebugEntryType.ENTRY_TYPE_DATA_READ | SMALDebugEntryType.ENTRY_TYPE_DATA_WRITE):
        return "data"
    return "transition"


def construct_c_codegen_context(*_args: Any, **_kwargs: Any) -> CCodegenContext:
    """Construct a jinja2 template rendering context for SMAL debugging boilerplate code (C).

    Returns:
        CCodegenContext: The context for generating SMAL debugging boilerplate code (C).

    """
    return CCodegenContext(
        enums=[CEnumData.from_py_enum(SMALDebugEntryType)],
        structs=[
            CStructData.from_model(SMALDebugTransitionPayload),
            CStructData.from_model(SMALDebugMessagePayload),
            CStructData.from_model(SMALDebugDataPayload),
            CStructData.from_model(SMALDebugErrorPayload),
            CStructData.from_model(SMALDebugEntry),
            CStructData.from_model(SMALDebugRing),
            CStructData.from_model(SMALFlushStatus),
        ],
        # TODO: Is there a better way to represent this?
        unions=[
            CUnionData(
                "smal_dbg_payload_t",
                {
                    "transition": (SMALDebugTransitionPayload.C_DATATYPE, "Payload for state transition entries"),
                    "message": (SMALDebugMessagePayload.C_DATATYPE, "Payload for event/command entries"),
                    "data": (SMALDebugDataPayload.C_DATATYPE, "Payload for data read/write entries"),
                    "error": (SMALDebugErrorPayload.C_DATATYPE, "Payload for error entries"),
                    "raw_words[2]": ("uint32_t", "For raw access to the payload as two 32-bit words, if needed"),
                },
            ),
        ],
        definition_order=[
            "smal_dbg_entry_type_t",
            "smal_dbg_transition_payload_t",
            "smal_dbg_message_payload_t",
            "smal_dbg_data_payload_t",
            "smal_dbg_error_payload_t",
            "smal_dbg_payload_t",
            "smal_dbg_entry_t",
            "smal_dbg_ring_t",
            "smal_dbg_flush_status_t",
        ],
    )
