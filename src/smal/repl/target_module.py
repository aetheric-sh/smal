"""Module defining a dataclass describing a target module for the SMAL REPL.

This is the python file that contains target-specific implementations for data harvesting and device connection.
"""

from __future__ import annotations  # Until Python 3.14

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from smal.repl.cmd_sets.debug import HarvestFn
    from smal.repl.connection import ConnectFn


@dataclass(frozen=True)
class TargetModule:
    """Dataclass describing a target module for the SMAL REPL."""

    filepath: Path
    connect_fn: ConnectFn
    harvest_fn: HarvestFn
