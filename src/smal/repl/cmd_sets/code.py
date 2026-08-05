"""Module defining the `code` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

import cmd2


class CodeCmdSet(cmd2.CommandSet):
    """Command set for handling code in the SMAL REPL."""
