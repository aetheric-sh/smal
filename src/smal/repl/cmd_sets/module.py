"""Module defining the `module` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import TYPE_CHECKING

import cmd2
from pydantic import BaseModel

from smal.repl.helpers import get_parent_app

if TYPE_CHECKING:
    import argparse

_module_parser = cmd2.Cmd2ArgumentParser()
_module_parser.add_subparsers(title="subcommand", help="subcommand help")

_set_parser = cmd2.Cmd2ArgumentParser()
_set_parser.add_argument("filepath", type=Path, completer=cmd2.Cmd.path_complete, help="Path to the module definition file (.py) containing the `harvest` and `connect` functions.")

_info_parser = cmd2.Cmd2ArgumentParser()


class SetArgs(BaseModel):
    """Model describing the arguments to the set command."""

    filepath: Path


class ModuleCmdSet(cmd2.CommandSet):
    """Command set for handling modules in the SMAL REPL."""

    @cmd2.with_argparser(_module_parser)
    def do_module(self, args: argparse.Namespace) -> None:
        """Manage SMAL modules.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        handler = args.cmd2_handler.get()
        if handler is not None:
            handler(args)
        else:
            self._cmd.poutput("No subcommand given.")
            self._cmd.do_help("module")

    @cmd2.as_subcommand_to("module", "set", _set_parser, help="Set the module definition file for the SMAL REPL.")
    def module_set(self, args: argparse.Namespace) -> None:
        """Set the module definition file for the SMAL REPL.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = SetArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        parent_app.set_active_module(parsed_args.filepath)

    @cmd2.as_subcommand_to("module", "info", _info_parser, help="Display information about the currently active module.")
    def module_info(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused argument
        """Display information about the currently active module.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        active_module = parent_app.get_active_module()
        if active_module is None:
            parent_app.print_warning("No active module. Set one with the `module set` command.", omit_heading=True)
        else:
            info_str = ",\n- ".join([f"{k}: {v}" for k, v in vars(active_module).items()])
            parent_app.print_msg(f"[bold green]Active module Info:[/bold green]\n- {info_str}")
