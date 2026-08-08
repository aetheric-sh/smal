"""Module defining utilities for pydantic schemas in SMAL."""

from __future__ import annotations  # Until Python 3.14

from typing import ClassVar

import semver
from pydantic import field_validator

from smal.codegen.primitives.smal_primitive import SMALPrimitive


class IdentifierValidationMixin:
    """Mixin class allowing a model to be identifiable."""

    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    @field_validator(*IDENTIFIER_FIELDS, check_fields=False)
    @classmethod
    def validate_name_is_valid_identifier(cls, v: str) -> str:
        """Validate that the given name is a valid identifier.

        Args:
            v (str): The name to validate.

        Raises:
            ValueError: If the name is not a valid identifier.

        Returns:
            str: The validated name.

        """
        if not v.isidentifier():
            raise ValueError(f"Invalid identifier: {v}")
        return v


class SemverValidationMixin:
    """Mixin class allowing a model to have a validated semantic version."""

    SEMVER_FIELDS: ClassVar[tuple[str]] = ("version",)

    @field_validator(*SEMVER_FIELDS, check_fields=False)
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Validate the incoming semantic version.

        Args:
            v (str): The semantic version string to validate.

        Returns:
            str: The validated semantic version string.

        """
        semver.Version.parse(v)  # exceptions are raised
        return v


class PrimitiveValidationMixin:
    """Mixin class allowing a model to have a validated SMAL primitive type."""

    TYPE_FIELDS: ClassVar[tuple[str]] = ("type",)

    @field_validator(*TYPE_FIELDS, check_fields=False)
    @classmethod
    def validate_primitive_type(cls, v: str) -> str:
        """Validate the incoming primitive type is a valid SMALPrimitive.

        Args:
            v (str): The incoming primitive type string to validate.

        Raises:
            ValueError: If the incoming primitive type is not a valid SMALPrimitive.

        Returns:
            str: The validated primitive type string.

        """
        if not SMALPrimitive.is_smal_primitive(v):
            raise ValueError(f"Invalid primitive type: '{v}'. Must be one of: {', '.join({sp.value for sp in SMALPrimitive})}")
        return v
