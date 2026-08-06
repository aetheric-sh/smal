"""Module defining the main entrypoint for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

import platform
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cmd2
from pydantic import BaseModel
from rich.console import Console

from smal.repl.cmd_sets import CodeCmdSet, CorrectionsCmdSet, DebugCmdSet, DiagramCmdSet, MachineCmdSet, ModuleCmdSet, MsgCmdSet, RulesCmdSet, ValidateCmdSet
from smal.repl.connection import ConnectFn, DeviceConnection
from smal.repl.helpers import echo_list, import_external_fn_from_file, parse_key_value, parse_params
from smal.repl.target_module import TargetModule
from smal.utilities import constants as SMALConstants
from smal.utilities.persistence import SMALPersistence

if TYPE_CHECKING:
    import argparse

    from smal.repl.cmd_sets.debug import HarvestFn
    from smal.schemas.state_machine import StateMachine

_connect_parser = cmd2.Cmd2ArgumentParser()
_connect_parser.add_argument("-m", "--module", type=Path, completer=cmd2.Cmd.path_complete, help="The path to the module containing the connect function for your device.")
_connect_parser.add_argument(
    "-p",
    "--param",
    action="append",
    type=parse_key_value,
    help="Repeatable key=value pair (e.g., -p key1=value1 -p key2=value2) to pass additional parameters to the connect function.",
)


class ConnectArgs(BaseModel):
    """Model describing the arguments to the connect command."""

    module: Path | None = None
    param: list[tuple[str, Any]] | None = None


_cinfo_parser = cmd2.Cmd2ArgumentParser()

_disconnect_parser = cmd2.Cmd2ArgumentParser()
_disconnect_parser.add_argument(
    "-p",
    "--param",
    action="append",
    type=parse_key_value,
    help="Repeatable key=value pair (e.g., -p key1=value1 -p key2=value2) to pass additional parameters to the disconnect function.",
)


class DisconnectArgs(BaseModel):
    """Model describing the arguments to the disconnect command."""

    param: list[tuple[str, Any]] | None = None


class SMALREPL(cmd2.Cmd):
    """Class defining the main REPL for the SMAL tool."""

    prompt = f"{SMALConstants.REPL_NAME}> "
    intro = f"Welcome to the {SMALConstants.APP_NAME_FULL} REPL. Type ? to list commands."

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the SMAL REPL."""
        super().__init__(*args, **kwargs)
        self._active_machine: StateMachine | None = None  # Placeholder for the active machine object
        self._active_connection: DeviceConnection | None = None  # Placeholder for the active connection object
        self._active_module: TargetModule | None = None  # Placeholder for the active module
        self._machine_paths_to_names: dict[Path, str] = {}  # Placeholder for the machine paths to names mapping
        self._machine_names_to_objs: dict[str, StateMachine] = {}  # Placeholder for the machine map
        self.console = Console()
        self.register_command_set(CodeCmdSet())
        self.register_command_set(CorrectionsCmdSet())
        self.register_command_set(DebugCmdSet())
        self.register_command_set(DiagramCmdSet())
        self.register_command_set(MachineCmdSet())
        self.register_command_set(ModuleCmdSet())
        self.register_command_set(MsgCmdSet())
        self.register_command_set(RulesCmdSet())
        self.register_command_set(ValidateCmdSet())
        self._update_prompt()

    def postcmd(self, stop: bool, statement: cmd2.Statement | str) -> bool:
        """Refresh the prompt after each command so it reflects the current connection/machine state.

        Args:
            stop (bool): Whether the command loop should stop.
            statement (cmd2.Statement | str): The statement that was executed.

        Returns:
            bool: The unmodified `stop` value.

        """
        self._update_prompt()
        return super().postcmd(stop, statement)

    @cmd2.with_argparser(_connect_parser)
    def do_connect(self, args: argparse.Namespace) -> None:
        """Connect to an arbitrary device.

        Args:
            args (argparse.Namespace): The parsed command-line arguments containing the module path and optional keyword arguments for the connect function.

        """
        if self._active_connection is not None and self._active_connection.is_connected:
            self.console.print(f"[bold red]Already connected to device: {self._active_connection.name}. Disconnect first with the `disconnect` command.[/bold red]")
            return
        parsed_args = ConnectArgs.model_validate(vars(args))
        try:
            extra_kwargs: dict[str, Any] = parse_params(parsed_args.param or [])
        except ValueError as e:
            self.print_error(f"Failed to process connection arguments: {e}")
            return
        try:
            module = args.module or (self._active_module.filepath if self._active_module else None)
            self.console.print(f"[bold blue]Attempting connection to device using module {module}...[/bold blue]")
            self._active_connection = DeviceConnection.create(self, self._active_module, args.module, **extra_kwargs)
            if self._active_connection is not None:
                self.print_success(f"Connected to device: {self._active_connection.name}")
            else:
                self.print_error(f"Connection failed using module {module}. No device returned.")
        except Exception as e:  # noqa: BLE001 - Broad exception caught for user-facing error handling
            self.print_error(f"Failed to connect using module {module}: {e}")

    @cmd2.with_argparser(_cinfo_parser)
    def do_cinfo(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused method argument
        """Display information about the current device connection.

        Args:
            args (argparse.Namespace): The parsed command-line arguments (not used in this command).

        """
        if self._active_connection is None or not self._active_connection.is_connected:
            self.console.print("[bold red]No active device connection.[/bold red]")
            return
        self.console.print(f"[bold green]Active device connection:[/bold green] {self._active_connection.name}")
        self.console.print("[bold magenta]Connection details:[/bold magenta]")
        self.console.print(self._active_connection.connection_details_str or "[bold yellow]No connection details available.[/bold yellow]")

    @cmd2.with_argparser(_disconnect_parser)
    def do_disconnect(self, args: argparse.Namespace) -> None:
        """Disconnect from the active device connection, if there is one.

        Args:
            args (argparse.Namespace): The parsed command-line arguments containing optional keyword arguments for the disconnect function.

        """
        parsed_args = DisconnectArgs.model_validate(vars(args))
        try:
            extra_kwargs: dict[str, Any] = parse_params(parsed_args.param or [])
        except ValueError as e:
            self.print_error(f"Failed to process disconnection arguments: {e}")
            return
        self._disconnect_from_device(**extra_kwargs)

    def do_clean(self, arg: str) -> None:  # noqa: ARG002 - Unused method argument
        """Clean the SMAL persisted application data directory.

        Args:
            arg (str): Unused argument.

        """
        app_dir = SMALPersistence.DEFAULT_PATH.parent
        if not app_dir.exists():
            self.console.print("[bold yellow]Nothing to clean — no application data directory found.[/bold yellow]")
            return
        confirmation = self.read_input(f"Are you sure you want to delete the application data directory at {app_dir}? [y/N] ")
        if confirmation.strip().lower() not in {"y", "yes"}:
            self.console.print("[bold yellow]Cancelled — application data directory was not removed.[/bold yellow]")
            return
        SMALPersistence.clean()
        self.console.print(f"[bold green]Removed application data directory: {app_dir}[/bold green]")

    def do_graphviz(self, arg: str) -> None:  # noqa: ARG002 - Unused method argument
        """Check for Graphviz installation and provide installation instructions if not found.

        Args:
            arg (str): Unused argument.

        """
        with self.console.status("[bold blue]Checking for Graphviz (`dot`) installation...[/bold blue]"):
            dot_path = shutil.which("dot")
            if dot_path:
                self.console.print(f"✅ [green]Graphviz is already installed[/green] at: [cyan]{dot_path}[/cyan]")
                return
            self.console.print("❌ [red]Graphviz not found.[/red]")
            system = platform.system()
            match system:
                case "Windows":
                    self.console.print("➡️  [bold]Windows detected[/bold].")
                    self.console.print("Install Graphviz using the official installer:")
                    self.console.print("[cyan]https://graphviz.org/download/[/cyan]")
                    echo_list("Recommended", ["Download the 'Graphviz Windows Installer (EXE)'", "Run it and check 'Add Graphviz to the system PATH'"], tab_size=4)
                case "Darwin":
                    self.console.print("➡️  [bold]macOS detected[/bold].")
                    echo_list("Install Graphviz with Homebrew", ["[code]brew install graphviz[/code]"], tab_size=4, bold_header=False)
                    echo_list("Or download from", ["https://graphviz.org/download/"], tab_size=4, bold_header=False)
                    if shutil.which("brew"):
                        self.console.print("🍺  [green]Homebrew detected[/green] — running install command...")
                        subprocess.run(["brew", "install", "graphviz"], check=True)
                case "Linux":
                    self.console.print("➡️  [bold]Linux detected[/bold].")
                    echo_list(
                        "Install Graphviz using your package manager",
                        ["Debian/Ubuntu: [code]sudo apt install graphviz[/code]", "Fedora: [code]sudo dnf install graphviz[/code]", "Arch: [code]sudo pacman -S graphviz[/code]"],
                        tab_size=4,
                        bold_header=False,
                    )
                    echo_list("Or download from", ["https://graphviz.org/download/"], tab_size=4, bold_header=False)
                case _:
                    self.console.print(f"⚠️  [yellow]Unsupported OS[/yellow]: {system}")
                    echo_list("Please install Graphviz manually from", ["https://graphviz.org/download/"], tab_size=4, bold_header=False)
            echo_list("Once installed, verify your installation with", ["[code]dot -V[/code]"], tab_size=4, bold_header=False)

    def do_exit(self, arg: str) -> bool:  # noqa: ARG002 - Unused method argument
        """Exit the REPL.

        Args:
            arg (str): Unused argument.

        Returns:
            bool: True if the REPL should exit, False otherwise.

        """
        self._disconnect_from_device()
        return True

    def do_EOF(self, arg: str) -> bool:  # noqa: ARG002 - Unused method argument
        """Exit the REPL on EOF (Ctrl+D).

        Args:
            arg (str): Unused argument.

        Returns:
            bool: True if the REPL should exit, False otherwise.

        """
        self.console.print("\n[bold blue] EOF (Ctrl+D) detected, exiting SMAL REPL...[/bold blue]")
        self._disconnect_from_device()
        return True

    def get_console(self) -> Console:
        """Get the rich console for the REPL.

        Returns:
            Console: The rich console object.

        """
        return self.console

    def get_active_machine(self) -> StateMachine | None:
        """Get the currently active state machine.

        Returns:
            StateMachine | None: The currently active state machine, or None if no machine is active.

        """
        return self._active_machine

    def set_active_machine(self, machine: StateMachine) -> None:
        """Set the currently active state machine.

        Args:
            machine (StateMachine): The state machine to set as active.

        """
        self._active_machine = machine

    def cache_machine(self, fp: Path, machine: StateMachine) -> None:
        """Cache the given state machine object for the specified file path.

        Args:
            fp (Path): The file path of the state machine definition.
            machine (StateMachine): The state machine object to cache.

        """
        self._machine_paths_to_names[fp] = machine.name
        self._machine_names_to_objs[machine.name] = machine

    def get_machine_name(self, path: Path) -> str | None:
        """Get the name of the state machine associated with the given file path.

        Args:
            path (Path): The file path of the state machine definition.

        Returns:
            str | None: The name of the state machine, or None if not found.

        """
        return self._machine_paths_to_names.get(path)

    def get_machine_by_name(self, name: str) -> StateMachine | None:
        """Get the state machine object associated with the given name.

        Args:
            name (str): The name of the state machine.

        Returns:
            StateMachine | None: The state machine object, or None if not found.

        """
        return self._machine_names_to_objs.get(name)

    def get_machine_by_path(self, path: Path) -> StateMachine | None:
        """Get the state machine object associated with the given file path.

        Args:
            path (Path): The file path of the state machine definition.

        Returns:
            StateMachine | None: The state machine object, or None if not found.

        """
        name = self._machine_paths_to_names.get(path)
        if name is None:
            return None
        return self._machine_names_to_objs.get(name)

    def get_cached_machines(self) -> dict[str, StateMachine]:
        """Get the cached state machines.

        Returns:
            dict[str, StateMachine]: A dictionary mapping state machine names to their corresponding objects.

        """
        return self._machine_names_to_objs

    def get_machine_path(self, name: str) -> Path | None:
        """Get the file path associated with the given state machine name.

        Args:
            name (str): The name of the state machine.

        Returns:
            Path | None: The file path of the state machine definition, or None if not found.

        """
        for path, machine_name in self._machine_paths_to_names.items():
            if machine_name == name:
                return path
        return None

    def get_active_connection(self) -> DeviceConnection | None:
        """Get the currently active device connection.

        Returns:
            DeviceConnection | None: The currently active device connection, or None if no connection is active.

        """
        return self._active_connection

    def print_msg(self, message: str) -> None:
        """Print a message to the console.

        Args:
            message (str): The message to print.

        """
        self.console.print(message)

    def print_success(self, message: str, prefix: str | None = None, omit_heading: bool = False) -> None:
        """Print a success message to the console.

        Args:
            message (str): The success message to print.
            prefix (str | None): An optional prefix for the message. If provided, it will be displayed before the message.
            omit_heading (bool): If True, the "Success: " heading will be omitted from the message.

        """
        msg = f"{prefix + ' ' if prefix else ''}[bold green]{'Success: ' if not omit_heading else ''}{message}[/bold green]"
        self.console.print(msg)

    def print_warning(self, message: str, prefix: str | None = None, omit_heading: bool = False) -> None:
        """Print a warning message to the console.

        Args:
            message (str): The warning message to print.
            prefix (str | None): An optional prefix for the message. If provided, it will be displayed before the message.
            omit_heading (bool): If True, the "Warning: " heading will be omitted from the message.

        """
        msg = f"{prefix + ' ' if prefix else ''}[bold yellow]{'Warning: ' if not omit_heading else ''}{message}[/bold yellow]"
        self.console.print(msg)

    def print_error(self, message: str, prefix: str | None = None, omit_heading: bool = False) -> None:
        """Print an error message to the console.

        Args:
            message (str): The error message to print.
            prefix (str | None): An optional prefix for the message. If provided, it will be displayed before the message.
            omit_heading (bool): If True, the "Error: " heading will be omitted from the message.

        """
        msg = f"{prefix + ' ' if prefix else ''}[bold red]{'Error: ' if not omit_heading else ''}{message}[/bold red]"
        self.console.print(msg)

    def set_active_module(self, module_file: Path) -> None:
        """Set the active module for the REPL.

        Args:
            module_file (Path): The path to the module file to set as active.

        """
        if not module_file.is_file():
            self.print_error(f"Module file not found: {module_file}")
            return
        self._active_module = module_file
        connect_fn: ConnectFn = import_external_fn_from_file(module_file, "smal_connect_module", "connect")
        harvest_fn: HarvestFn = import_external_fn_from_file(module_file, "smal_harvest_module", "harvest")
        self._active_module = TargetModule(filepath=module_file, connect_fn=connect_fn, harvest_fn=harvest_fn)
        self.print_success(f"Active module set to: {module_file}", omit_heading=True)

    def get_active_module(self) -> TargetModule | None:
        """Get the currently active module for the REPL.

        Returns:
            TargetModule | None: The currently active module, or None if no module is active.

        """
        return self._active_module

    def _disconnect_from_device(self, **kwargs: Any) -> None:
        if self._active_connection is None or not self._active_connection.is_connected:
            self.console.print("[bold green]No active device connection to disconnect from.[/bold green]")
            return
        device_name = self._active_connection.name
        self.print_warning(f"Active device connection detected, attempting to disconnect {device_name}...")
        try:
            with self.console.status(f"[bold blue]Disconnecting from device {device_name}...[/bold blue]"):
                if self._active_connection.disconnect(**kwargs):
                    self.print_success(f"Successfully disconnected from device {device_name}.")
                else:
                    self.print_error(f"Failed to disconnect from device {device_name}.")
        except Exception as e:  # noqa: BLE001 - Broad exception caught for user-facing error handling
            self.print_error(f"Error occurred while disconnecting from device {device_name}: {e}.")

    def _update_prompt(self) -> None:
        """Update the prompt with the active machine and connection names."""
        stylized_connection_str = self._active_connection.connection_info_str if self._active_connection else cmd2.stylize("disconnected", "bold red")
        stylized_machine_str = cmd2.stylize(self._active_machine.name, "bold green") if self._active_machine else cmd2.stylize("NULL_MACHINE", "bold red")
        self.prompt = f"{SMALConstants.REPL_NAME}[{stylized_connection_str}]({stylized_machine_str})> "


def main() -> None:
    """Run the main entrypoint for the SMAL REPL."""
    repl = SMALREPL()
    repl.cmdloop()


if __name__ == "__main__":
    main()
