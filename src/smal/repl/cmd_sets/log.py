"""Module defining the `log` command set for the SMAL REPL."""

from __future__ import annotations

from typing import TYPE_CHECKING

import cmd2

from smal.repl.cmd_sets.smal_cmd_set import SMALCmdSet

if TYPE_CHECKING:
    import argparse

_log_parser = cmd2.Cmd2ArgumentParser()
_log_parser.add_subparsers(title="subcommand", help="subcommand help")

_view_parser = cmd2.Cmd2ArgumentParser()


class LogCmdSet(SMALCmdSet):
    """Command set for interacting with SMAL's persistent log file."""

    @cmd2.with_argparser(_log_parser)
    def do_log(self, args: argparse.Namespace) -> None:
        """Manage the SMAL log file.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        handler = args.cmd2_handler.get()
        if handler is not None:
            handler(args)
        else:
            self._cmd.poutput("No subcommand given.")
            self._cmd.do_help("log")

    @cmd2.as_subcommand_to("log", "view", _view_parser, help="View the contents of SMAL's persistent log file.")
    def log_view(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused argument
        """View the contents of SMAL's persistent log file.

        The file is only read and printed to the terminal here — nothing about viewing it is itself logged, so
        repeated `log view` calls don't pollute the log they're displaying.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parent_app = self.parent_app
        log_path = parent_app.logger.log_path
        if not log_path.is_file():
            parent_app.print_warning(f"No log file found at {log_path}.")
            return
        contents = log_path.read_text(encoding="utf-8")
        if not contents.strip():
            parent_app.print_msg(f"Log file at {log_path} is empty.")
            return
        self._cmd.ppaged(contents)
