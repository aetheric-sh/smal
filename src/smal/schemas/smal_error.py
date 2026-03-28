from typing import ClassVar

from pydantic import BaseModel, Field

from smal.schemas.utilities import IdentifierValidationMixin


class SMALError(IdentifierValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str = Field(..., description="A unique name for the error, which serves as its identifier and may be used in transitions or other contexts.")
    id: int | None = Field(
        default=None, description="A unique integer identifier for the error. If not provided, it may be auto-assigned based on the order of definition or other criteria."
    )
    description: str | None = Field(default=None, description="Description of the error, if any.")
