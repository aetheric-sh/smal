from pydantic import BaseModel, Field
from typing import Any, Literal, ClassVar
from smal.schemas.utilities import IdentifierValidationMixin, PrimitiveValidationMixin

class SMALCommandParameter(IdentifierValidationMixin, PrimitiveValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)
    TYPE_FIELDS: ClassVar[tuple[str]] = ("type",)

    name: str
    type: str
    default_value: Any = Field(default=None, description="The default value of the parameter, if any.")

class SMALCommandPayloadField(IdentifierValidationMixin, PrimitiveValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)
    TYPE_FIELDS: ClassVar[tuple[str]] = ("type",)

    name: str
    type: str

class SMALCommandPayload(BaseModel):
    fields: list[SMALCommandPayloadField] = Field(default_factory=list, description="Fields of the command payload, if any.")

class SMALCommand(IdentifierValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str
    direction: Literal["host_to_device", "device_to_host", "internal"]
    transport: Literal["ble", "protobuf", "uart", "spi", "i2c", "custom"]
    parameters: list[SMALCommandParameter] = Field(default_factory=list, description="Optional command parameters")
    payload: SMALCommandPayload | None = Field(default=None, description="Optional command payload.")
