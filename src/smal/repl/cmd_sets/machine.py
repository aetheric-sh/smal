"""Module defining the `machine` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import TYPE_CHECKING

import cmd2

from smal.repl.helpers import get_parent_app
from smal.schemas.state_machine import SMALFile

if TYPE_CHECKING:
    import argparse

load_parser = cmd2.Cmd2ArgumentParser()
load_parser.add_argument("-f", "--file", type=Path, help="Path to the machine definition file (.smal, .yaml, .yml) to load.", required=True)
load_parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite the existing machine if it already exists in the cache.")


class MachineCmdSet(cmd2.CommandSet):
    """Command set for handling machines in the SMAL REPL."""

    @cmd2.with_argparser(load_parser)
    def do_load(self, args: argparse.Namespace) -> None:
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
            except ValueError:
                console.print(f"[bold red]Error: Invalid machine definition file: {args.file}[/bold red]")
                return
