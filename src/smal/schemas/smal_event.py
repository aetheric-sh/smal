from typing import ClassVar

from pydantic import BaseModel, Field

from smal.schemas.utilities import IdentifierValidationMixin


class SMALEvent(IdentifierValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str = Field(..., description="A unique name for the event, which serves as its identifier and may be used in transitions.")
    id: int | None = Field(
        default=None, description="A unique integer identifier for the event. If not provided, it may be auto-assigned based on the order of definition or other criteria."
    )
