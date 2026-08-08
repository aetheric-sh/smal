"""Module defining an extension to cmd2's builtin `alias` command for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from typing import TYPE_CHECKING

import cmd2

from smal.repl.cmd_sets.smal_cmd_set import SMALCmdSet
from smal.repl.helpers import echo_table

if TYPE_CHECKING:
    import argparse

_table_parser = cmd2.Cmd2ArgumentParser()


class AliasCmdSet(SMALCmdSet):
    """Command set extending cmd2's builtin `alias` command with a `table` subcommand."""

    @cmd2.as_subcommand_to("alias", "table", _table_parser, help="Show all aliases in a table.")
    def alias_table(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused argument
        """Show all aliases in a table.

        Args:
            args (argparse.Namespace): The parsed command-line arguments (not used in this command).

        """
        parent_app = self.parent_app
        aliases = self._cmd.aliases
        if not aliases:
            parent_app.print_msg("No aliases found. Create one with the `alias create` command.")
            return
        alias_data = [[name, value] for name, value in sorted(aliases.items())]
        echo_table(
            "Aliases",
            ["Name", "Value"],
            alias_data,
            col_metadata={
                "Name": {"style": "cyan"},
                "Value": {"style": "green"},
            },
        )
