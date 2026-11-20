"""State machine errors."""

from __future__ import annotations  # Until Python 3.14

from typing import TypeAlias

from smal.schemas.enumeration import EnumMember

Error: TypeAlias = EnumMember  # Errors are just enum members, but we want to distinguish them in the schema for clarity
