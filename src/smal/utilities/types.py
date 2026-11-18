"""Reusable types for SMAL."""

from __future__ import annotations

from typing import Annotated, Any

import semver
from pydantic import BeforeValidator, Field, PlainSerializer

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")]
"""String representing an identifier."""


def _parse_semver(v: Any) -> semver.Version:
    if isinstance(v, semver.Version):
        return v
    return semver.Version.parse(str(v))  # Raises ValueError on bad input


SemVer = Annotated[semver.Version, BeforeValidator(_parse_semver), PlainSerializer(str, return_type=str)]
"""A parsed and validated semantic version (major.minor.patch). Serializes to string."""
