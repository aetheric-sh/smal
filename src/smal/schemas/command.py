"""Module defining the Command model for representing commands in a state machine."""

from __future__ import annotations  # Until Python 3.14

from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field

from smal.schemas.utilities import IdentifierValidationMixin, PrimitiveValidationMixin


class CommandParameter(IdentifierValidationMixin, PrimitiveValidationMixin, BaseModel):
    """Schema defining an individual parameter of a command."""

    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)
    TYPE_FIELDS: ClassVar[tuple[str]] = ("type",)

    name: str = Field(..., description="The name of the command parameter.")
    type: str = Field(..., description="The datatype of the command parameter.")
    default_value: Any = Field(default=None, description="The default value of the parameter, if any.")


class CommandPayloadField(IdentifierValidationMixin, PrimitiveValidationMixin, BaseModel):
    """Schema defining an individual field within a command payload."""

    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)
    TYPE_FIELDS: ClassVar[tuple[str]] = ("type",)

    name: str = Field(..., description="The name of the command payload field.")
    type: str = Field(..., description="The datatype of the command payload field.")


class CommandPayload(BaseModel):
    """Schema defining the payload of a command."""

    fields: list[CommandPayloadField] = Field(default_factory=list, description="Fields of the command payload, if any.")


class Command(IdentifierValidationMixin, BaseModel):
    """Schema defining a command for a state machine."""

    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str = Field(..., description="The name of the command.")
    direction: Literal["host_to_device", "device_to_host", "internal"] = Field(..., description="The direction of the command, in the embedded device context.")
    transport: Literal["ble", "protobuf", "uart", "spi", "i2c", "custom"] = Field(..., description="The transport over which the command will be sent.")
    parameters: list[CommandParameter] = Field(default_factory=list, description="Optional command parameters")
    payload: CommandPayload | None = Field(default=None, description="Optional command payload.")
