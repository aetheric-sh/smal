"""State machine events."""

from __future__ import annotations  # Until Python 3.14

from typing import TypeAlias

from smal.schemas.enumeration import EnumMember

Event: TypeAlias = EnumMember  # Events are just enum members, but we want to distinguish them in the schema for clarity
