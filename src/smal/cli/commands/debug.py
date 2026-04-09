"""Module defining the debug CLI command."""

from __future__ import annotations  # Until Python 3.14

import importlib.util
import sys
from pathlib import Path  # noqa: TC003 - Typer needs this
from typing import Any, Protocol

import typer
from rich.console import Console
from rich.markup import escape

from smal.cli.commands.helpers import echo_table, prefer_inner_rich_statuses
from smal.schemas.debug import SMALDebugEntry, SMALDebugEntryType
from smal.schemas.state_machine import SMALFile, StateMachine


class HarvestFunc(Protocol):
    """Protocol for the harvest function, which accepts a machine name and arbitrary default params."""

    def __call__(self, name: str, **kwargs: Any) -> bytearray:
        """Harvest debug data for the given machine name."""
        ...

def _format_payload_details(entry: SMALDebugEntry, sm: StateMachine) -> str:
    payload = entry.payload
    if not hasattr(payload, "display"):
        raise RuntimeError(f"Payload for entry type {entry.entry_type} does not have a display method. This is a programming error.")
    # Escape Rich markup so literal brackets in transition displays (e.g. [event]) are preserved.
    return escape(payload.display(sm))


def _display_entries(entries: list[SMALDebugEntry], sm: StateMachine) -> None:
    """Display debug entries in a rich table format.

    Args:
        entries: List of SMALDebugEntry objects to display.
        sm: Optional state machine context used for ID-to-name resolution.

    """
    row_data = [
        [
            str(idx),
            f"{entry.timestamp_ms}",
            SMALDebugEntryType.formatted_display(entry.entry_type),
            _format_payload_details(entry, sm),
        ]
        for idx, entry in enumerate(entries, start=1)
    ]
    echo_table(
        f"SMAL Debug Log Entries ({sm.name})",
        ["#", "Timestamp (ms)", "Entry Type", "Details"],
        row_data,
        col_metadata={
            "#": {"style": "cyan"},
            "Timestamp (ms)": {"style": "green"},
            "Entry Type": {"style": "yellow"},
            "Details": {"style": "white"},
        },
    )


def debug_cmd(
    smal_path: Path = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the input SMAL file.",
    ),
    script_path: Path = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the Python script containing the harvest_smal_dbg_data function.",
    ),
    hvst_kwarg: list[str] = typer.Option(  # noqa: B008
        [],
        "--hvst-kwarg",
        "-H",
        help="Additional key=value pairs to pass as kwargs to the harvest function. Can be used multiple times for multiple kwargs.",
    ),
) -> None:
    """Debug a SMAL state machine using a custom debug data function.

    This command loads a SMAL file and a Python script. It then attempts to find and import
    a function called 'harvest_smal_dbg_data' from the script, which should accept the state
    machine name (str) and return debug data as a bytearray.

    Note:
        The harvest script must have all its third-party dependencies pre-installed in the
        same Python environment that SMAL is running in. Install them separately before running this command.

    Args:
        smal_path: The path to the SMAL file to debug.
        script_path: The path to the Python script containing the harvest_smal_dbg_data function.
        hvst_kwarg: Additional key=value pairs to pass as kwargs to the harvest function defined by script_path.

    Raises:
        typer.Exit: If the SMAL file cannot be loaded, script cannot be imported,
            function is not found, or the function call fails.

    """
    # For rich console output
    console = Console()
    # Parse extra CLI args (--key value pairs) into kwargs for harvest_func
    extra_kwargs: dict[str, Any] = {}
    for hkwarg in hvst_kwarg:
        if "=" not in hkwarg:
            console.print(f"[red]Invalid --hvst-kwarg value: '{hkwarg}'. Expected format: key=value[/red]")
            raise typer.Exit(code=2)
        key, value = hkwarg.split("=", 1)
        key = key.strip().lstrip("-")
        value = value.strip()
        extra_kwargs[key] = value
        if not key:
            console.print(f"[red]Invalid --hvst-kwarg key in: '{hkwarg}'. Key cannot be empty.[/red]")
            raise typer.Exit(code=2)
        if value.lower() in {"true", "false"}:
            extra_kwargs[key] = value.lower() == "true"
        elif value.isdigit():
            extra_kwargs[key] = int(value)
        else:
            extra_kwargs[key] = value  # Keep as string if not bool or int
    # Load the SMAL file to get the state machine
    with console.status(f"Loading SMAL file: [bold cyan]{smal_path}[/bold cyan]", spinner="dots"):
        try:
            smal = SMALFile.from_file(smal_path)
            machine_name = smal.name
        except FileNotFoundError as e:
            console.print(f"[red]SMAL file not found: {smal_path}[/red]")
            raise typer.Exit(code=1) from e
        except ValueError as e:
            console.print(f"[red]Invalid SMAL file {smal_path}: {e}[/red]")
            raise typer.Exit(code=1) from e
    # Dynamically import the script and find the harvest function
    with console.status(f"Importing data harvesting script: [bold cyan]{script_path}[/bold cyan]", spinner="dots"):
        spec = importlib.util.spec_from_file_location("debug_module", script_path)
        if spec is None or spec.loader is None:
            console.print(f"[red]Failed to import script {script_path}[/red]")
            raise typer.Exit(code=1)
        module = importlib.util.module_from_spec(spec)
        sys.modules["debug_module"] = module
        try:
            spec.loader.exec_module(module)
        except ModuleNotFoundError as e:
            console.print(
                f"[red]Failed to import script {script_path}:[/red]\n"
                f"[yellow]Missing dependency: {e.name}[/yellow]\n\n"
                "[cyan]To fix this, install the required dependencies into the same Python virtual environment as SMAL:[/cyan]\n"
                f"[yellow]  pip install {e.name}[/yellow]",
            )
            raise typer.Exit(code=1) from e
        except ImportError as e:
            console.print(
                f"[red]Failed to import script {script_path}:[/red]\n"
                f"[yellow]{e}[/yellow]\n\n"
                "[cyan]The script or one of its dependencies could not be imported.[/cyan]\n"
                "[cyan]Make sure all required dependencies are installed in the same Python virtual environment as SMAL:[/cyan]\n"
                "[yellow]  pip install <dependency_name>[/yellow]",
            )
            raise typer.Exit(code=1) from e
    # Get the "harvest" function provided by the script the user gave us
    if not hasattr(module, "harvest"):
        console.print(f"[red]Required function 'harvest' not found in {script_path}[/red]")
        raise typer.Exit(code=1)
    harvest_func: HarvestFunc = module.harvest
    if not callable(harvest_func):
        console.print("[red]Required function 'harvest' is not callable[/red]")
        raise typer.Exit(code=1)
    # Now, harvest the data using the imported function, passing the machine name and any extra kwargs from the CLI
    with (
        prefer_inner_rich_statuses(),  # To allow the imported harvest function to use its own status spinners without flicker
        console.status(
            f"Gathering debug data for state machine: [bold cyan]{machine_name}[/bold cyan]",
            spinner="dots",
        ),
    ):
        try:
            raw_data = harvest_func(machine_name, **extra_kwargs)
        except Exception as e:
            console.print(f"[red]Failed to harvest debug data: {e}[/red]")
            raise typer.Exit(code=1) from e
        if not isinstance(raw_data, bytearray):
            console.print(f"[red]Harvest function returned {type(raw_data).__name__}, expected bytearray[/red]")
            raise typer.Exit(code=1)
    # Deserialize the debug data into SMALDebugEntry objects
    with console.status(f"Deserializing debug entries: [bold cyan]{len(raw_data)} bytes[/bold cyan]", spinner="dots"):
        try:
            entries = SMALDebugEntry.deserialize_entries_from_bytes(raw_data)
        except ValueError as e:
            console.print(f"[red]Failed to deserialize debug data: {e}[/red]")
            raise typer.Exit(code=1) from e
    # Success
    console.print(
        f"[green]Successfully deserialized [cyan]{len(entries)} debug entries[/cyan] for [bold]{machine_name}[/bold]:[/green] ",
    )
    # Display the entries in a rich table
    console.print()
    _display_entries(entries, smal)
