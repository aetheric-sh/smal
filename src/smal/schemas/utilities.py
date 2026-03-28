from pydantic import field_validator
import semver
from typing import ClassVar
from smal.smal_primitive import SMALPrimitive

class IdentifierValidationMixin:
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    @field_validator(*IDENTIFIER_FIELDS, check_fields=False)
    def validate_name_is_valid_identifier(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError(f"Invalid identifier: {v}")
        return v


class SemverValidationMixin:
    SEMVER_FIELDS: ClassVar[tuple[str]] = ("version",)

    @field_validator(*SEMVER_FIELDS, check_fields=False)
    def validate_semver(cls, v: str) -> str:
        try:
            semver.Version.parse(v)
        except (ValueError, TypeError):
            raise
        return v

class PrimitiveValidationMixin:
    TYPE_FIELDS: ClassVar[tuple[str]] = ("type",)

    @field_validator(*TYPE_FIELDS, check_fields=False)
    def validate_primitive_type(cls, v: str) -> str:
        if not SMALPrimitive.is_smal_primitive(v):
            raise ValueError(f"Invalid primitive type: '{v}'. Must be one of: {', '.join({sp.value for sp in SMALPrimitive})}")
        return v
