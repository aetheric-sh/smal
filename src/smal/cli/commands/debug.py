"""Module defining the debug CLI command."""

from __future__ import annotations  # Until Python 3.14

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.table import Table

from smal.schemas.debug import (
    SMALDebugEntry,
    SMALDebugEntryType,
    deserialize_debug_entries,
)
from smal.schemas.state_machine import SMALFile, StateMachine

if TYPE_CHECKING:
    from collections.abc import Callable

debug_app = typer.Typer(help="Debug a SMAL state machine using custom debug data.")

debug_data = bytearray(
    [
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        0,
        1,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        0,
        1,
        0,
        15,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        0,
        1,
        0,
        16,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        0,
        1,
        0,
        2,
        0,
        0,
        0,
        64,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        207,
        192,
        0,
        0,
        1,
        0,
        0,
        0,
        64,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        208,
        192,
        0,
        0,
        1,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        0,
        5,
        0,
        12,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        5,
        0,
        5,
        0,
        23,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        5,
        0,
        5,
        0,
        24,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        5,
        0,
        6,
        0,
        27,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        6,
        0,
        6,
        0,
        29,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        6,
        0,
        2,
        0,
        3,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        2,
        0,
        2,
        0,
        18,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        2,
        0,
        4,
        0,
        12,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        4,
        0,
        4,
        0,
        19,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        4,
        0,
        11,
        0,
        17,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        11,
        0,
        10,
        0,
        22,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        10,
        0,
        0,
        0,
        11,
        0,
        0,
        0,
    ]
)


def _format_entry_type(entry_type: int) -> str:
    """Format entry type bitmask as a human-readable string."""
    types = []
    if entry_type & SMALDebugEntryType.STATE_TRANSITION:
        types.append("TRANSITION")
    if entry_type & SMALDebugEntryType.EVENT_RX:
        types.append("EVT_RX")
    if entry_type & SMALDebugEntryType.EVENT_TX:
        types.append("EVT_TX")
    if entry_type & SMALDebugEntryType.CMD_RX:
        types.append("CMD_RX")
    if entry_type & SMALDebugEntryType.CMD_TX:
        types.append("CMD_TX")
    if entry_type & SMALDebugEntryType.DATA_READ:
        types.append("DATA_RD")
    if entry_type & SMALDebugEntryType.DATA_WRITE:
        types.append("DATA_WR")
    if entry_type & SMALDebugEntryType.ERROR:
        types.append("ERROR")
    return ", ".join(types) if types else "NONE"


def _format_payload_details(entry: SMALDebugEntry, sm: StateMachine | None = None) -> str:
    """Format payload details as a human-readable string."""
    payload = entry.payload
    if hasattr(payload, "entry_type"):
        if payload.entry_type == "transition":
            if sm is not None:
                return payload.display(sm)
            return f"src={payload.src_state:5d} tgt={payload.tgt_state:5d} evt={payload.evt:5d} status={payload.status:6d}"
        if payload.entry_type == "error":
            return f"code={payload.error_code:8d} detail=0x{payload.detail:08x}"
        if payload.entry_type == "message":
            return f"id={payload.identifier:5d} len={payload.data_len:5d} val=0x{payload.value:08x}"
        if payload.entry_type == "data":
            return f"addr=0x{payload.address:08x} len={payload.data_len:8d}"
    return "N/A"


def _display_entries(console: Console, entries: list[SMALDebugEntry], sm: StateMachine | None = None) -> None:
    """Display debug entries in a rich table format.

    Args:
        console: Rich console for output.
        entries: List of SMALDebugEntry objects to display.
        sm: Optional state machine context used for ID-to-name resolution.

    """
    table = Table(title="Debug Log Entries", show_header=True, header_style="bold magenta")
    table.add_column("#", style="cyan", width=6)
    table.add_column("Timestamp (ms)", style="green", width=14)
    table.add_column("Entry Type", style="yellow", width=30)
    table.add_column("Details", style="white", width=60)

    for idx, entry in enumerate(entries, start=1):
        entry_type_str = _format_entry_type(entry.entry_type)
        details = _format_payload_details(entry, sm)
        table.add_row(
            str(idx),
            f"{entry.timestamp_ms:>12d}",
            entry_type_str,
            details,
        )

    console.print(table)


@debug_app.callback(invoke_without_command=True)
def debug_root(
    smal_path: Path = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the input SMAL file.",
    ),
    _script_path: Path = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the Python script containing the harvest_smal_dbg_data function.",
    ),
) -> None:
    """Debug a SMAL state machine using a custom debug data function.

    This command loads a SMAL file and a Python script. It then attempts to find and import
    a function called 'harvest_smal_dbg_data' from the script, which should accept the state
    machine name (str) and return debug data as a bytearray.

    Args:
        smal_path: The path to the SMAL file to debug.
        script_path: The path to the Python script containing the harvest_smal_dbg_data function.

    Raises:
        typer.Exit: If the SMAL file cannot be loaded, script cannot be imported,
            function is not found, or the function call fails.

    """
    console = Console()
    sm = SMALFile.from_file(smal_path)
    deserialized_entries = deserialize_debug_entries(debug_data)
    _display_entries(console, deserialized_entries, sm)

    # # Load the SMAL file to get the state machine name
    # with console.status(f"Loading SMAL file: [bold cyan]{smal_path}[/bold cyan]", spinner="dots"):
    #     try:
    #         smal = SMALFile.from_file(smal_path)
    #         machine_name = smal.state_machine.name
    #     except FileNotFoundError as e:
    #         console.print(f"[red]SMAL file not found: {smal_path}[/red]")
    #         raise typer.Exit(code=1) from e
    #     except ValueError as e:
    #         console.print(f"[red]Invalid SMAL file {smal_path}: {e}[/red]")
    #         raise typer.Exit(code=1) from e

    # # Dynamically import the script and find the harvest_smal_dbg_data function
    # with console.status(f"Importing script: [bold cyan]{script_path}[/bold cyan]", spinner="dots"):
    #     try:
    #         spec = importlib.util.spec_from_file_location("debug_module", script_path)
    #         if spec is None or spec.loader is None:
    #             raise ImportError(f"Could not create module spec for {script_path}")
    #         module = importlib.util.module_from_spec(spec)
    #         sys.modules["debug_module"] = module
    #         spec.loader.exec_module(module)
    #     except (ImportError, OSError) as e:
    #         console.print(f"[red]Failed to import script {script_path}: {e}[/red]")
    #         raise typer.Exit(code=1) from e

    # # Get the harvest_smal_dbg_data function
    # try:
    #     if not hasattr(module, "harvest_smal_dbg_data"):
    #         raise AttributeError("harvest_smal_dbg_data not found in module")
    #     harvest_func: Callable[[str], bytearray] = module.harvest_smal_dbg_data
    #     if not callable(harvest_func):
    #         raise TypeError("harvest_smal_dbg_data is not callable") from None
    # except AttributeError as e:
    #     console.print(f"[red]Function 'harvest_smal_dbg_data' not found in {script_path}: {e}[/red]")
    #     raise typer.Exit(code=1) from e
    # except TypeError as e:
    #     console.print(f"[red]Function 'harvest_smal_dbg_data' is not callable: {e}[/red]")
    #     raise typer.Exit(code=1) from e

    # # Call the harvest function with the state machine name
    # with console.status(
    #     f"Gathering debug data for machine: [bold cyan]{machine_name}[/bold cyan]",
    #     spinner="dots",
    # ):
    #     try:
    #         debug_data = harvest_func(machine_name)
    #         if not isinstance(debug_data, bytearray):
    #             raise TypeError(f"harvest_smal_dbg_data returned {type(debug_data).__name__}, expected bytearray")
    #     except TypeError as e:
    #         console.print(f"[red]{e}[/red]")
    #         raise typer.Exit(code=1) from e
    #     except Exception as e:
    #         console.print(f"[red]Failed to harvest debug data: {e}[/red]")
    #         raise typer.Exit(code=1) from e

    # # Deserialize the debug data into SMALDebugEntry objects
    # with console.status(
    #     f"Deserializing debug entries: [bold cyan]{len(debug_data)} bytes[/bold cyan]",
    #     spinner="dots",
    # ):
    #     try:
    #         entries = deserialize_debug_entries(debug_data)
    #     except ValueError as e:
    #         console.print(f"[red]Failed to deserialize debug data: {e}[/red]")
    #         raise typer.Exit(code=1) from e

    # # Success
    # console.print(
    #     f"[green]Successfully deserialized debug entries for [bold]{machine_name}[/bold]:[/green] [cyan]{len(entries)} entries[/cyan]",
    # )

    # # Display the entries in a rich table
    # console.print()
    # _display_entries(console, entries)
