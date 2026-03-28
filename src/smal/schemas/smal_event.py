from pydantic import BaseModel
from smal.schemas.utilities import IdentifierValidationMixin
from typing import ClassVar

class SMALEvent(IdentifierValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str
    id: int