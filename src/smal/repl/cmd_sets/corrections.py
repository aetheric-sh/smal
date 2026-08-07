"""Module defining the `corrections` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from typing import TYPE_CHECKING

import cmd2
from pydantic import BaseModel

from smal.repl.completers import correction_completer
from smal.repl.helpers import echo_table, get_parent_app, get_persistence
from smal.utilities.corrections import ALL_CORRECTIONS

if TYPE_CHECKING:
    import argparse

_corrections_parser = cmd2.Cmd2ArgumentParser()
_corrections_parser.add_subparsers(title="subcommand", help="subcommand help")

_list_parser = cmd2.Cmd2ArgumentParser()

_enable_parser = cmd2.Cmd2ArgumentParser()
_enable_parser.add_argument("name", type=str, completer=correction_completer, help="The name of the correction to enable, or 'all' to enable all.")


class EnableArgs(BaseModel):
    """Model describing the arguments to the enable command."""

    name: str


_disable_parser = cmd2.Cmd2ArgumentParser()
_disable_parser.add_argument("name", type=str, completer=correction_completer, help="The name of the correction to disable, or 'all' to disable all.")


class DisableArgs(BaseModel):
    """Model describing the arguments to the disable command."""

    name: str


class CorrectionsCmdSet(cmd2.CommandSet):
    """Command set for handling corrections in the SMAL REPL."""

    @cmd2.with_argparser(_corrections_parser)
    def do_corrections(self, args: argparse.Namespace) -> None:
        """Manage SMAL state machine corrections.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        handler = args.cmd2_handler.get()
        if handler is not None:
            handler(args)
        else:
            self._cmd.poutput("No subcommand given.")
            self._cmd.do_help("corrections")

    @cmd2.as_subcommand_to("corrections", "enable", _enable_parser, help="Enable 1 or more corrections to be applied.")
    def corrections_enable(self, args: argparse.Namespace) -> None:
        """Enable 1 or more corrections to be applied to the active SMAL machine.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        Raises:
            RuntimeError: If the `CorrectionsCmdSet` is not registered with a parent cmd2 application.

        """
        parsed_args = EnableArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        persistence = get_persistence()
        if parsed_args.name.lower() == "all":
            for c in ALL_CORRECTIONS:
                persistence.enable_correction(c.name, True, write_to_file=False)
            parent_app.print_success("All corrections have been enabled.")
        else:
            correction = next((c for c in ALL_CORRECTIONS if c.name == parsed_args.name), None)
            if correction is None:
                parent_app.print_error(f"Unknown correction '{parsed_args.name}'. Run the `smal corrections` command for list of valid corrections.")
                return
            persistence.enable_correction(correction.name, True, write_to_file=False)
            parent_app.print_success(f"Correction '{correction.name}' has been enabled.")
        persistence.save()

    @cmd2.as_subcommand_to("corrections", "disable", _disable_parser, help="Disable 1 or more corrections from being applied.")
    def corrections_disable(self, args: argparse.Namespace) -> None:
        """Disable 1 or more corrections from being applied to the active SMAL state machine.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        Raises:
            RuntimeError: If the `CorrectionsCmdSet` is not registered with a parent cmd2 application.

        """
        parsed_args = DisableArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        persistence = get_persistence()
        if parsed_args.name.lower() == "all":
            for c in ALL_CORRECTIONS:
                persistence.enable_correction(c.name, False, write_to_file=False)
            parent_app.print_success("All corrections have been disabled.")
        else:
            correction = next((c for c in ALL_CORRECTIONS if c.name == parsed_args.name), None)
            if correction is None:
                parent_app.print_error(f"Unknown correction '{parsed_args.name}'. Run the `smal corrections` command for list of valid corrections.")
                return
            persistence.enable_correction(correction.name, False, write_to_file=False)
            parent_app.print_success(f"Correction '{correction.name}' has been disabled.")
        persistence.save()

    @cmd2.as_subcommand_to(
        "corrections",
        "list",
        _list_parser,
        help="List all corrections that SMAL can apply to state machines. Invoking `smal corrections` invokes this as well.",
    )
    def corrections_list(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused method argument
        """List all available corrections in the SMAL corrections set and their statuses.

        Args:
            args (argparse.Namespace): The parsed command-line arguments. Unused.

        """
        persistence = get_persistence()
        # Persistence should always have all corrections in its corrections dict
        corrections = [next(c for c in ALL_CORRECTIONS if c.name == correction_name) for correction_name in persistence.corrections]
        corrections_data = [[c.name, str(persistence.is_correction_enabled(c)), c.description] for c in corrections]
        echo_table(
            "SMAL Corrections",
            ["Name", "Enabled", "Description"],
            corrections_data,
            col_metadata={
                "Name": {"style": "cyan"},
                "Enabled": {"style": "green"},
                "Description": {"style": "yellow"},
            },
        )
