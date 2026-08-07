"""Module defining the `module` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import TYPE_CHECKING, Any

import cmd2
from pydantic import BaseModel

from smal.repl.helpers import echo_table, get_parent_app, get_persistence

if TYPE_CHECKING:
    import argparse

_module_parser = cmd2.Cmd2ArgumentParser()
_module_parser.add_subparsers(title="subcommand", help="subcommand help")

_load_parser = cmd2.Cmd2ArgumentParser()
_load_parser.add_argument(
    "filepath",
    type=Path,
    completer=cmd2.Cmd.path_complete,
    help="Path to the module definition file (.py) containing the `harvest` and `connect` functions.",
)
_load_parser.add_argument(
    "-n",
    "--name",
    type=str,
    help="Optional name for the module. If not provided, the module's filename (without extension) will be used as the name.",
)
_load_parser.add_argument(
    "-c",
    "--cache",
    action="store_false",
    help="Cache the module path for future use (default: True).",
)
_load_parser.add_argument(
    "-o",
    "--overwrite",
    action="store_true",
    help="Overwrite the cached module path if it already exists (default: False).",
)


class LoadArgs(BaseModel):
    """Model describing the arguments to the set command."""

    filepath: Path
    name: str | None = None
    cache: bool = True
    overwrite: bool = False


_info_parser = cmd2.Cmd2ArgumentParser()


def _module_completer(cmd: cmd2.Cmd, text: str, line: str, begidx: int, endidx: int, *args: Any, **kwargs: Any) -> list[str]:  # noqa: ARG001 - Unused arguments
    persistence = get_persistence()
    values = list(persistence.modules.keys())
    return [v for v in values if v.startswith(text)]


_switch_parser = cmd2.Cmd2ArgumentParser()
_switch_parser.add_argument(
    "name",
    type=str,
    completer=_module_completer,
    help="Name of the module to switch to. Use `module list` to see available modules.",
)


class SwitchArgs(BaseModel):
    """Model describing the arguments to the switch command."""

    name: str


_list_parser = cmd2.Cmd2ArgumentParser()


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

    @cmd2.as_subcommand_to("module", "load", _load_parser, help="Load the module definition file for the SMAL REPL.")
    def module_load(self, args: argparse.Namespace) -> None:
        """Load the module definition file for the SMAL REPL.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = LoadArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        parent_app.set_active_module(parsed_args.filepath)
        persistence = get_persistence()
        if parsed_args.cache:
            persistence.add_module(parsed_args.name or parsed_args.filepath.stem, parsed_args.filepath, overwrite=parsed_args.overwrite, save=True)

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
            parent_app.print_warning("No active module. Load one with the `module load` command.", omit_heading=True)
        else:
            echo_table(
                "Active Module Info",
                ["Hook Name", "Signature", "Address"],
                active_module.info,
                col_metadata={
                    "Hook Name": {"style": "cyan"},
                    "Signature": {"style": "green"},
                    "Address": {"style": "yellow"},
                },
                show_lines=True,
            )
            parent_app.print_msg(f"[bold cyan]Module Location: {active_module.filepath}[/bold cyan]")

    @cmd2.as_subcommand_to("module", "switch", _switch_parser, help="Switch to a different cached module.")
    def module_switch(self, args: argparse.Namespace) -> None:
        """Switch to a different cached module.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = SwitchArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        persistence = get_persistence()
        module_path = persistence.modules.get(parsed_args.name)
        if module_path is None:
            parent_app.print_error(f"No cached module found with the name '{parsed_args.name}'. Use `module list` to see available modules.", omit_heading=True)
            return
        parent_app.set_active_module(module_path)

    @cmd2.as_subcommand_to("module", "list", _list_parser, help="List all cached modules.")
    def module_list(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused argument
        """List all cached modules.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        persistence = get_persistence()
        if not persistence.modules:
            parent_app.print_msg("No cached modules found.")
            return
        module_data = [[name, str(path)] for name, path in persistence.modules.items()]
        echo_table(
            "Cached Modules",
            ["Name", "File Path"],
            module_data,
            col_metadata={
                "Name": {"style": "cyan"},
                "File Path": {"style": "green"},
            },
        )
