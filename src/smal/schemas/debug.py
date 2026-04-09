"""Module defining the schema for the debug structure for SMAL state machines."""

from __future__ import annotations  # Until Python 3.14

import struct
from enum import IntFlag
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from smal.schemas.state_machine import StateMachine


class SMALDebugEntryType(IntFlag):
    """Enumeration of debug entry types (bitfield flags)."""

    NONE = 0x00
    STATE_TRANSITION = 0x01
    EVENT_RX = 0x02
    EVENT_TX = 0x04
    CMD_RX = 0x08
    CMD_TX = 0x10
    DATA_READ = 0x20
    DATA_WRITE = 0x40
    ERROR = 0x80


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
        """Return a human-readable string representation of the transition payload."""

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

        src_name = resolve_state_name(self.src_state)
        tgt_name = resolve_state_name(self.tgt_state)
        evt_name = resolve_event_name(self.evt)
        return f"{src_name}({self.src_state}) --<{evt_name}({self.evt})>--> {tgt_name}({self.tgt_state})"
        # return f"{src_name} ({self.src_state}) -> {tgt_name} ({self.tgt_state}) on {evt_name} ({self.evt}), status={self.status}"


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


def deserialize_debug_entries(data: bytearray) -> list[SMALDebugEntry]:
    """Deserialize a bytearray containing binary smal_dbg_entry_t structures into a list of SMALDebugEntry objects.

    The bytearray should contain a series of 16-byte debug entries, each consisting of (little-endian):
    - entry_type (uint32, 4 bytes): Bitmask indicating the type of entry
    - timestamp_ms (uint32, 4 bytes): Timestamp when the entry was logged
    - payload (8 bytes): Union of various payload types interpreted by entry_type

    Payload format for STATE_TRANSITION entries:
    - src_state (uint16): Source state ID/index before transition
    - tgt_state (uint16): Target state ID/index after transition
    - evt (uint16): Event ID/index that triggered the transition
    - status (int16): Status of the transition

    Args:
        data: Bytearray containing serialized debug entries (16 bytes each), little-endian format.

    Returns:
        List of SMALDebugEntry objects ordered by occurrence in the data.

    Raises:
        ValueError: If data length is not a multiple of 16 or payload unpacking fails.

    """
    entry_bytes = data
    entry_size = 16

    entries: list[SMALDebugEntry] = []
    for i in range(0, len(entry_bytes), entry_size):
        chunk = entry_bytes[i : i + entry_size]
        # Unpack header (little-endian): entry_type (uint32) | timestamp_ms (uint32)
        entry_type, timestamp_ms = struct.unpack("<II", chunk[0:8])
        payload_bytes = chunk[8:16]

        # Determine payload type based on entry_type bitmask and parse accordingly
        payload_dict: dict = {"entry_type": _get_payload_type(entry_type)}

        if entry_type & SMALDebugEntryType.STATE_TRANSITION:
            # Unpack payload (little-endian): src_state (u16) | tgt_state (u16) | evt (u16) | status (i16)
            src_state, tgt_state, evt, status = struct.unpack("<HHHH", payload_bytes[0:8])
            status = struct.unpack("<h", struct.pack("<H", status))[0]  # Convert unsigned to signed
            payload_dict.update(
                {
                    "src_state": src_state,
                    "tgt_state": tgt_state,
                    "evt": evt,
                    "status": status,
                },
            )
        elif entry_type & SMALDebugEntryType.ERROR:
            error_code, detail = struct.unpack("<iI", payload_bytes[0:8])
            payload_dict.update({"error_code": error_code, "detail": detail})
        elif entry_type & (SMALDebugEntryType.EVENT_RX | SMALDebugEntryType.EVENT_TX | SMALDebugEntryType.CMD_RX | SMALDebugEntryType.CMD_TX):
            identifier, data_len, value = struct.unpack("<HHI", payload_bytes[0:8])
            payload_dict.update(
                {
                    "identifier": identifier,
                    "data_len": data_len,
                    "value": value,
                },
            )
        elif entry_type & (SMALDebugEntryType.DATA_READ | SMALDebugEntryType.DATA_WRITE):
            address, data_len = struct.unpack("<II", payload_bytes[0:8])
            payload_dict.update({"address": address, "data_len": data_len})
        else:
            # Default to transition payload if no specific type matched
            src_state, tgt_state, evt, status = struct.unpack("<HHHH", payload_bytes[0:8])
            status = struct.unpack("<h", struct.pack("<H", status))[0]
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
