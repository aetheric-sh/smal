"""Module defining the schema for the debug structures for SMAL state machines."""

from __future__ import annotations  # Until Python 3.14

import struct
from enum import IntFlag
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from smal.schemas.state_machine import StateMachine


class SMALDebugEntryType(IntFlag):
    """Enumeration of debug entry types (bitfield flags)."""

    NONE = 0
    STATE_TRANSITION = 1 << 0
    EVENT_RX = 1 << 1
    EVENT_TX = 1 << 2
    CMD_RX = 1 << 3
    CMD_TX = 1 << 4
    DATA_READ = 1 << 5
    DATA_WRITE = 1 << 6
    ERROR = 1 << 7
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
        if entry_type & SMALDebugEntryType.STATE_TRANSITION:
            types.append("TRANSITION")
        if entry_type & SMALDebugEntryType.EVENT_RX:
            types.append("EVT_RX")
        if entry_type & SMALDebugEntryType.EVENT_TX:
            types.append("EVT_TX")
        if entry_type & SMALDebugEntryType.CMD_RX:
            types.append("CMD_RX")
        if entry_type & SMALDebugEntryType.CMD_TX:
            types.append("CMD_TX")
        if entry_type & SMALDebugEntryType.DATA_READ:
            types.append("DATA_RD")
        if entry_type & SMALDebugEntryType.DATA_WRITE:
            types.append("DATA_WR")
        if entry_type & SMALDebugEntryType.ERROR:
            types.append("ERROR")
        return ", ".join(types) if types else "NONE"


class SMALDebugTransitionPayload(BaseModel):
    """Payload for state transition debug entries."""

    entry_type: Literal["transition"] = Field(default="transition", exclude=True)
    src_state: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Source state ID or index before the transition.",
    )
    tgt_state: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Target state ID or index after the transition.",
    )
    evt: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Event ID or index that triggered the transition.",
    )
    status: int = Field(
        ...,
        ge=-32768,
        le=32767,
        description="Status of the transition (success, failure, error code, etc.).",
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

    entry_type: Literal["message"] = Field(default="message", exclude=True)
    identifier: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Event or command ID/index.",
    )
    data_len: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Length of data associated with the event or command, in bytes.",
    )
    value: int = Field(
        ...,
        ge=0,
        le=0xFFFFFFFF,
        description="Value associated with the event or command (parameter, status code, etc.).",
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

    entry_type: Literal["data"] = Field(default="data", exclude=True)
    address: int = Field(
        ...,
        ge=0,
        le=0xFFFFFFFF,
        description="Address that was read from or written to.",
    )
    data_len: int = Field(
        ...,
        ge=0,
        le=0xFFFFFFFF,
        description="Length of data that was read or written, in bytes.",
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

    entry_type: Literal["error"] = Field(default="error", exclude=True)
    error_code: int = Field(
        ...,
        ge=-2147483648,
        le=2147483647,
        description="Error code (negative for error types, non-negative for specific codes).",
    )
    detail: int = Field(
        ...,
        ge=0,
        le=0xFFFFFFFF,
        description="Additional error detail (address, value, bitmask, etc.).",
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


SMALDebugPayload = Annotated[
    SMALDebugTransitionPayload | SMALDebugMessagePayload | SMALDebugDataPayload | SMALDebugErrorPayload,
    Field(discriminator="entry_type"),
]


class SMALDebugEntry(BaseModel):
    """Debug entry structure representing a single debug log entry."""

    entry_type: int = Field(
        ...,
        ge=0,
        le=0xFFFFFFFF,
        description="Bitmask indicating the type of entry (state transition, event, command, data read/write, error, etc.).",
    )
    timestamp_ms: int = Field(
        ...,
        ge=0,
        le=0xFFFFFFFF,
        description="Timestamp in milliseconds when the entry was logged.",
    )
    payload: SMALDebugPayload = Field(
        ...,
        description="The payload of the entry, interpreted based on entry_type.",
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
            if entry_type & SMALDebugEntryType.STATE_TRANSITION:
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
            elif entry_type & SMALDebugEntryType.ERROR:
                error_code, detail = struct.unpack(error_fmt, payload_bytes[0:payload_size_bytes])
                payload_dict.update({"error_code": error_code, "detail": detail})
            elif entry_type & (SMALDebugEntryType.EVENT_RX | SMALDebugEntryType.EVENT_TX | SMALDebugEntryType.CMD_RX | SMALDebugEntryType.CMD_TX):
                identifier, data_len, value = struct.unpack(message_fmt, payload_bytes[0:payload_size_bytes])
                payload_dict.update(
                    {
                        "identifier": identifier,
                        "data_len": data_len,
                        "value": value,
                    },
                )
            elif entry_type & (SMALDebugEntryType.DATA_READ | SMALDebugEntryType.DATA_WRITE):
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

    oldest_index: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Index of the oldest entry in the ring buffer.",
    )
    write_index: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Index where the next entry will be written.",
    )
    entry_count: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Number of valid entries currently in the ring.",
    )
    capacity: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Maximum number of entries the ring can hold.",
    )
    overwrite_count: int = Field(
        ...,
        ge=0,
        le=0xFFFF,
        description="Number of times entries have been overwritten.",
    )
    entries: list[SMALDebugEntry] = Field(
        ...,
        description="Array of debug entries in the ring buffer.",
    )


def _get_payload_type(entry_type: int) -> str:
    """Determine the payload type discriminator based on entry_type bitmask.

    Args:
        entry_type: The entry_type bitmask from the debug entry.

    Returns:
        The discriminator string for the payload type.

    """
    if entry_type & SMALDebugEntryType.STATE_TRANSITION:
        return "transition"
    if entry_type & SMALDebugEntryType.ERROR:
        return "error"
    if entry_type & (SMALDebugEntryType.EVENT_RX | SMALDebugEntryType.EVENT_TX | SMALDebugEntryType.CMD_RX | SMALDebugEntryType.CMD_TX):
        return "message"
    if entry_type & (SMALDebugEntryType.DATA_READ | SMALDebugEntryType.DATA_WRITE):
        return "data"
    return "transition"


# TODO: Create introspection functions to provide data to the code generator for generating debug boilerplate code
