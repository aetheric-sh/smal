"""Module defining the `module` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cmd2
from pydantic import BaseModel

from smal.repl.cmd_sets.smal_cmd_set import SMALCmdSet
from smal.repl.completers import module_completer
from smal.repl.connection import DeviceConnection
from smal.repl.helpers import echo_table, get_fn_from_module, get_persistence, import_external_module_from_file, parse_key_value, parse_params
from smal.repl.target_module import TargetModule

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
    completer=module_completer,
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


_switch_parser = cmd2.Cmd2ArgumentParser()
_switch_parser.add_argument(
    "name",
    type=str,
    completer=module_completer,
    help="Name of the module to switch to. Use `module list` to see available modules.",
)


class SwitchArgs(BaseModel):
    """Model describing the arguments to the switch command."""

    name: str


_list_parser = cmd2.Cmd2ArgumentParser()


_test_parser = cmd2.Cmd2ArgumentParser()
_test_parser.add_argument(
    "filepath",
    type=Path,
    completer=cmd2.Cmd.path_complete,
    help="Path to the module definition file (.py) to test.",
)
_test_parser.add_argument(
    "-p",
    "--param",
    action="append",
    type=parse_key_value,
    help="Repeatable key=value pair (e.g., -p key1=value1 -p key2=value2) to pass as keyword arguments to the module's `connect` function.",
)


class TestArgs(BaseModel):
    """Model describing the arguments to the test command."""

    filepath: Path
    param: list[tuple[str, Any]] | None = None


class ModuleCmdSet(SMALCmdSet):
    """Command set for handling modules in the SMAL REPL."""

    @cmd2.with_argparser(_module_parser)
    def do_module(self, args: argparse.Namespace) -> None:
        """Manage SMAL modules.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        handler = getattr(args, "cmd2_subcommand_func", None)
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
        parent_app = self.parent_app
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
        parent_app = self.parent_app
        if parent_app.active_module is None:
            parent_app.print_warning("No active module. Load one with the `module load` command.", omit_heading=True)
        else:
            echo_table(
                "Active Module Info",
                ["Hook Name", "Signature", "Address"],
                parent_app.active_module.info,
                col_metadata={
                    "Hook Name": {"style": "cyan"},
                    "Signature": {"style": "green"},
                    "Address": {"style": "yellow"},
                },
                show_lines=True,
            )
            parent_app.print_msg(f"[bold cyan]Module Location: {parent_app.active_module.filepath}[/bold cyan]")

    @cmd2.as_subcommand_to("module", "switch", _switch_parser, help="Switch to a different cached module.")
    def module_switch(self, args: argparse.Namespace) -> None:
        """Switch to a different cached module.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = SwitchArgs.model_validate(vars(args))
        parent_app = self.parent_app
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
        parent_app = self.parent_app
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

    @cmd2.as_subcommand_to(
        "module",
        "test",
        _test_parser,
        help="Sanity-check a module file by connecting to and immediately disconnecting from a device, without affecting REPL state.",
    )
    def module_test(self, args: argparse.Namespace) -> None:
        """Sanity-check a module file by connecting to and immediately disconnecting from a device.

        Unlike `module load`/`module switch`, this does not change the REPL's active module or connection state —
        it only validates that the module is importable, defines `connect`/`harvest` with the right shape, and
        that `connect` actually succeeds and yields a device that can be cleanly disconnected again.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = TestArgs.model_validate(vars(args))
        parent_app = self.parent_app
        if not parsed_args.filepath.is_file():
            parent_app.print_error(f"Module file not found: {parsed_args.filepath}")
            return
        try:
            fn_module = import_external_module_from_file(parsed_args.filepath, "smal_test_module")
            connect_fn = get_fn_from_module(fn_module, parsed_args.filepath, "connect")
            harvest_fn = get_fn_from_module(fn_module, parsed_args.filepath, "harvest")
        except (ImportError, AttributeError, TypeError) as e:
            parent_app.print_error(f"Module failed validation: {e}")
            return
        send_msg_fn = None
        with contextlib.suppress(AttributeError):
            send_msg_fn = get_fn_from_module(fn_module, parsed_args.filepath, "send_msg")
        hooks = "connect, harvest" + (", send_msg" if send_msg_fn is not None else "")
        parent_app.print_success(f"Module structure OK — found hooks: {hooks}.", omit_heading=True)
        target_module = TargetModule(filepath=parsed_args.filepath, connect_fn=connect_fn, harvest_fn=harvest_fn, send_msg_fn=send_msg_fn)
        extra_kwargs = parse_params(parsed_args.param or [])
        try:
            with parent_app.console.status(f"[bold blue]Test-connecting using module {parsed_args.filepath}...[/bold blue]"):
                test_connection = DeviceConnection.create(parent_app, target_module, None, **extra_kwargs)
        except Exception as e:  # noqa: BLE001 - Broad exception caught for user-facing error handling
            parent_app.print_error(f"{e}")
            return
        if test_connection is None:
            parent_app.print_warning("'connect' returned no device (nothing to disconnect). Module structure is valid.")
            return
        parent_app.print_success(f"Successfully connected to test device: {test_connection.name}")
        try:
            with parent_app.console.status(f"[bold blue]Disconnecting from test device {test_connection.name}...[/bold blue]"):
                disconnected = test_connection.disconnect()
        except Exception as e:  # noqa: BLE001 - Broad exception caught for user-facing error handling
            parent_app.print_error(f"Connected successfully, but failed to disconnect from test device: {e}")
            return
        if disconnected:
            parent_app.print_success(f"Module '{parsed_args.filepath}' passed the connectivity test (connect + disconnect succeeded).", omit_heading=True)
        else:
            parent_app.print_warning(f"Connected successfully, but the device reported a failed disconnect for module '{parsed_args.filepath}'.")
