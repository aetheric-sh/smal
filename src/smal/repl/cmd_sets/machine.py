"""Module defining the `machine` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import TYPE_CHECKING

import cmd2

from smal.repl.helpers import echo_table, get_parent_app
from smal.schemas.state_machine import SMALFile

if TYPE_CHECKING:
    import argparse

machine_parser = cmd2.Cmd2ArgumentParser()
machine_parser.add_subparsers(title="subcommand", help="subcommand help")

load_parser = cmd2.Cmd2ArgumentParser()
load_parser.add_argument("file", type=Path, completer=cmd2.Cmd.path_complete, help="Path to the machine definition file (.smal, .yaml, .yml) to load.")
load_parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite the existing machine if it already exists in the cache.")


list_parser = cmd2.Cmd2ArgumentParser()

switch_parser = cmd2.Cmd2ArgumentParser()
switch_parser.add_argument("name", type=str, help="The name of the machine to switch to.")


class MachineCmdSet(cmd2.CommandSet):
    """Command set for handling machines in the SMAL REPL."""

    @cmd2.with_argparser(machine_parser)
    def do_machine(self, args: argparse.Namespace) -> None:
        """Manage SMAL state machines.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        handler = args.cmd2_handler.get()
        if handler is not None:
            handler(args)
        else:
            self._cmd.poutput("No subcommand given.")
            self._cmd.do_help("machine")

    @cmd2.as_subcommand_to("machine", "load", load_parser, help="Load a SMAL state machine definition")
    def machine_load(self, args: argparse.Namespace) -> None:
        """Load a SMAL state machine either from a file or from the cache if it has already been loaded before.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        Raises:
            RuntimeError: If the `MachineCmdSet` is not registered with a parent cmd2 application.
            TypeError: If the parent application is not of type `REPLLike`.

        """
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        console = parent_app.get_console()
        machine = parent_app.get_machine_by_path(args.file)
        if machine and not args.overwrite:
            parent_app.set_active_machine(machine)
            console.print(f"[bold green]Successfully loaded '{machine.name}' machine definition from cache.[/bold green]")
            return
        with console.status(f"[bold blue]Loading machine definition from file {args.file}...[/bold blue]"):
            try:
                smal = SMALFile.from_file(args.file)
                parent_app.set_active_machine(smal)
                parent_app.cache_machine(args.file, smal)
                console.print(f"[bold green]Successfully loaded machine definition from {args.file}.[/bold green]")
            except FileNotFoundError:
                console.print(f"[bold red]Error: File not found: {args.file}[/bold red]")
                return
            except ValueError as e:
                console.print(f"[bold red]Error: Invalid machine definition file: {args.file}: {e}[/bold red]")
                return

    @cmd2.as_subcommand_to("machine", "list", list_parser, help="List all loaded SMAL state machines")
    def machine_list(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused method argument
        """List all loaded SMAL state machines.

        Args:
            args (argparse.Namespace): The parsed command-line arguments. Unused.

        Raises:
            RuntimeError: If the `MachineCmdSet` is not registered with a parent cmd2 application.

        """
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        console = parent_app.get_console()
        machines = list(parent_app.get_cached_machines())
        if not machines:
            console.print("[bold yellow]No loaded machines found.[/bold yellow]")
            return
        machine_data = [(machine_name, str(parent_app.get_machine_path(machine_name))) for machine_name in machines]
        echo_table("Loaded SMAL Machines", ["Name", "Path"], machine_data)

    @cmd2.as_subcommand_to("machine", "switch", switch_parser, help="Switch to a different loaded SMAL state machine")
    def machine_switch(self, args: argparse.Namespace) -> None:
        """Switch to a different loaded SMAL state machine.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        Raises:
            RuntimeError: If the `MachineCmdSet` is not registered with a parent cmd2 application.

        """
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        console = parent_app.get_console()
        machine = parent_app.get_machine_by_name(args.name)
        if not machine:
            console.print(f"[bold red]Error: No loaded machine found with name '{args.name}'.[/bold red]")
            return
        parent_app.set_active_machine(machine)
        console.print(f"[bold green]Switched to machine '{machine.name}'.[/bold green]")
