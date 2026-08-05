"""Module defining the main entrypoint for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

import platform
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cmd2
from rich.console import Console

from smal.repl.cmd_sets import all_cmd_sets
from smal.repl.connection import DeviceConnection
from smal.repl.helpers import echo_list, parse_key_value, parse_params
from smal.utilities.persistence import SMALPersistence

if TYPE_CHECKING:
    import argparse

    from smal.schemas.state_machine import StateMachine

connect_parser = cmd2.Cmd2ArgumentParser()
connect_parser.add_argument("-m", "--module", type=Path, help="The path to the module containing the connect function for your device.", required=True)
connect_parser.add_argument(
    "-p",
    "--param",
    action="append",
    type=parse_key_value,
    help="Repeatable key=value pair (e.g., -p key1=value1 -p key2=value2) to pass additional parameters to the connect function.",
)

disconnect_parser = cmd2.Cmd2ArgumentParser()
disconnect_parser.add_argument(
    "-p",
    "--param",
    action="append",
    type=parse_key_value,
    help="Repeatable key=value pair (e.g., -p key1=value1 -p key2=value2) to pass additional parameters to the disconnect function.",
)


class SMALREPL(cmd2.Cmd):
    """Class defining the main REPL for the SMAL tool."""

    _APP_NAME: str = "State Machine Abstraction Language"
    _APP_NAME_ABBREV: str = "SMAL"
    _APP_NAME_FULL: str = f"{_APP_NAME} ({_APP_NAME_ABBREV})"
    _REPL_NAME: str = f"{_APP_NAME_ABBREV}".lower()

    prompt = f"{_REPL_NAME}> "
    intro = f"Welcome to the {_APP_NAME_FULL} REPL. Type ? to list commands."

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the SMAL REPL."""
        super().__init__(*args, **kwargs)
        self._active_machine: StateMachine | None = None  # Placeholder for the active machine object
        self._active_connection: DeviceConnection | None = None  # Placeholder for the active connection object
        self._machine_paths_to_names: dict[Path, str] = {}  # Placeholder for the machine paths to names mapping
        self._machine_names_to_objs: dict[str, StateMachine] = {}  # Placeholder for the machine map
        self.console = Console()
        acs = all_cmd_sets()
        for cmd_set in acs:
            self.register_command_set(cmd_set)

    def pre_prompt(self) -> None:
        """Update the prompt with the active machine and connection names."""
        stylized_connection_str = self._active_connection.connection_info_str if self._active_connection else cmd2.stylize("disconnected", "bold red")
        stylized_machine_str = cmd2.stylize(self._active_machine.name, "bold green") if self._active_machine else cmd2.stylize("NULL_MACHINE", "bold red")
        self.prompt = f"{self._REPL_NAME}[{stylized_connection_str}]({stylized_machine_str})> "

    @cmd2.with_argparser(connect_parser)
    def do_connect(self, args: argparse.Namespace) -> None:
        """Connect to an arbitrary device.

        Args:
            args (argparse.Namespace): The parsed command-line arguments containing the module path and optional keyword arguments for the connect function.

        """
        if self._active_connection is not None and self._active_connection.is_connected:
            self.console.print(f"[bold red]Already connected to device: {self._active_connection.name}. Disconnect first with the `disconnect` command.[/bold red]")
            return
        try:
            extra_kwargs: dict[str, Any] = parse_params(args.param)
        except ValueError as e:
            self.console.print(f"[bold red]Error processing connection arguments: {e}[/bold red]")
            return
        try:
            with self.console.status(f"[bold blue]Attempting connection to device using module {args.module}...[/bold blue]"):
                self._active_connection = DeviceConnection.create(fn_module_path=args.module, **extra_kwargs)
                if self._active_connection is not None:
                    self.console.print(f"[bold green]Connection successful! Connected to device: {self._active_connection.name}[/bold green]")
                else:
                    self.console.print(f"[bold red]Connection failed using module {args.module}. No device returned.[/bold red]")
        except Exception as e:  # noqa: BLE001 - Broad exception caught for user-facing error handling
            self.console.print(f"[bold red]Failed to connect using module {args.module}: {e}[/bold red]")
            return

    @cmd2.with_argparser(disconnect_parser)
    def do_disconnect(self, args: argparse.Namespace) -> None:
        """Disconnect from the active device connection, if there is one.

        Args:
            args (argparse.Namespace): The parsed command-line arguments containing optional keyword arguments for the disconnect function.

        """
        try:
            extra_kwargs: dict[str, Any] = parse_params(args.param)
        except ValueError as e:
            self.console.print(f"[bold red]Error processing disconnection arguments: {e}[/bold red]")
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
        # TODO: Prompt user to confirm deletion of the application data directory
        SMALPersistence.clean()
        self.console.print(f"[bold green]Removed application data directory: {app_dir}[/bold green]")

    def do_graphviz(self, arg: str) -> None:  # noqa: ARG002 - Unused method argument
        """Check for Graphviz installation and provide installation instructions if not found.

        Args:
            arg (str): Unused argument.

        """
        self.console.print("🔍 [bold]Checking for Graphviz (`dot`)...[/bold]")
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
        self._disconnect_from_device()
        return True

    def _disconnect_from_device(self, **kwargs: Any) -> None:
        if self._active_connection is None or not self._active_connection.is_connected:
            self.console.print("[bold green]No active device connection to disconnect from.[/bold green]")
            return
        self.console.print(f"[bold yellow]Active device connection detected, attempting to disconnect {self._active_connection.name}...[/bold yellow]")
        try:
            with self.console.status(f"[bold blue]Disconnecting from device {self._active_connection.name}...[/bold blue]"):
                if self._active_connection.disconnect(**kwargs):
                    self.console.print(f"[bold green]Successfully disconnected from device {self._active_connection.name}.[/bold green]")
                else:
                    self.console.print(f"[bold red]Failed to disconnect from device {self._active_connection.name}.[/bold red]")
        except Exception as e:  # noqa: BLE001 - Broad exception caught for user-facing error handling
            self.console.print(f"[bold red]Error occurred while disconnecting from device {self._active_connection.name}: {e}.[/bold red]")


def main() -> None:
    """Run the main entrypoint for the SMAL REPL."""
    repl = SMALREPL()
    repl.cmdloop()


if __name__ == "__main__":
    main()
