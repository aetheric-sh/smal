"""Module defining the `diagram` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

import cmd2


class DiagramCmdSet(cmd2.CommandSet):
    """Command set for generating diagrams in the SMAL REPL."""
