"""Module defining the `debug` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import cmd2
from rich.markup import escape

from smal.codegen.code_generator import SMALCodeGenerator
from smal.codegen.templates.builtin_templates import TemplateRegistry
from smal.repl.helpers import echo_table, get_parent_app, import_external_fn_from_file, parse_key_value, parse_params
from smal.schemas.debug import SMALDebugEntry, SMALDebugEntryType
from smal.schemas.state_machine import SMALFile

if TYPE_CHECKING:
    import argparse

    from smal.repl.connection import ConnectedDevice
    from smal.schemas.state_machine import StateMachine


run_parser = cmd2.Cmd2ArgumentParser()
run_parser.add_argument("-f", "--file", type=str, help="Path to the external Python file containing the harvest function.", required=True)
run_parser.add_argument(
    "-p",
    "--param",
    action="append",
    type=parse_key_value,
    help="Repeatable key=value pair (e.g., -p key1=value1 -p key2=value2) to pass additional parameters to the harvest function.",
)

gen_boilerplate_parser = cmd2.Cmd2ArgumentParser()
gen_boilerplate_parser.add_argument("-o", "--output-dir", type=str, help="Directory to output the generated boilerplate code.", required=True)
gen_boilerplate_parser.add_argument("-l", "--lang", type=str, choices=["c"], help="Programming language for the boilerplate code.", required=True)
gen_boilerplate_parser.add_argument("-f", "--filename", type=str, help="Optional filename for the generated boilerplate code. If not provided, a default name will be used.")
gen_boilerplate_parser.add_argument(
    "--force",
    action="store_true",
    help="Force overwrite of existing files in the output directory. If not set, existing files will not be overwritten.",
)


@runtime_checkable
class HarvestFn(Protocol):
    """Protocol for the harvest function, which accepts a machine name and arbitrary default params."""

    def __call__(self, name: str, connected_device: ConnectedDevice, **kwargs: Any) -> bytearray:
        """Harvest debug data for the given machine name."""
        ...


class DebugCmdSet(cmd2.CommandSet):
    """Command set for debugging in the SMAL REPL."""

    @cmd2.with_argparser(run_parser)
    def do_run(self, args: argparse.Namespace) -> None:
        """Run the SMAL debug data harvesting tool to harvest curated debug data from a connected device.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        Raises:
            RuntimeError: If the parent REPL application cannot be accessed or is not of the expected type.
            TypeError: If the harvest function does not match the expected signature.

        """
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        console = parent_app.get_console()
        active_connection = parent_app.get_active_connection()
        if active_connection is None:
            console.print("[bold red]Error: No active connection found. Please connect to a device first.[/bold red]")
            return
        active_machine = parent_app.get_active_machine()
        if active_machine is None:
            console.print("[bold red]Error: No active machine found. Please load a machine definition first.[/bold red]")
            return
        harvest_fn = import_external_fn_from_file(args.file, "harvest_module", "harvest")
        if not isinstance(harvest_fn, HarvestFn):
            raise TypeError(f"The 'harvest' function in {args.file} does not match the expected signature.")
        console.print(f"[bold blue] Harvesting data from machine '{active_machine.name}'...[/bold blue]")
        extra_kwargs: dict[str, Any] = parse_params(args.param)
        try:
            raw_data = harvest_fn(active_machine.name, active_connection.device, **extra_kwargs)
        except Exception as e:  # noqa: BLE001 - Catching all exceptions to provide user feedback in the REPL.
            console.print(f"[bold red]Error during harvest function execution: {e}[/bold red]")
            return
        with console.status(f"Deserializing debug entries: [bold cyan]{len(raw_data)} bytes[/bold cyan]"):
            try:
                entries = SMALDebugEntry.deserialize_entries_from_bytes(raw_data)
            except ValueError:
                console.print("[bold red]Error: Failed to deserialize debug entries from the harvested data.[/bold red]")
                return
        console.print(f"[bold green]Successfully harvested and deserialized {len(entries)} debug entries.[/bold green]")
        console.print()
        _display_entries(entries, active_machine)

    @cmd2.with_argparser(gen_boilerplate_parser)
    def do_gen_boilerplate(self, args: argparse.Namespace) -> None:
        """Generate boilerplate debugging code for a new project utilizing SMAL.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        Raises:
            RuntimeError: If the parent REPL application cannot be accessed or is not of the expected type.

        """
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        console = parent_app.get_console()
        # Validate output directory existence and writability
        if not args.output_dir.exists():
            args.output_dir.mkdir(parents=True, exist_ok=True)
        elif not args.output_dir.is_dir():
            console.print(f"[bold red]Error: Output path exists but is not a directory: {args.output_dir}[/bold red]")
        generator = SMALCodeGenerator()
        smal = SMALFile.blank()
        boilerplate_templates = TemplateRegistry.get_dbg_boilerplate_templates(args.lang)
        if not boilerplate_templates:
            console.print(f"[red]No debug boilerplate templates found for language: {args.lang}[/red]")
            return
        for tmpl in boilerplate_templates:
            console.print(f"[green]Generating debug boilerplate code for [cyan]{args.lang}[/cyan] using template: [bold cyan]{tmpl.name}[/bold cyan][/green]")
            _env, btmpl, smal_tmpl = generator.load_builtin_template(tmpl.name)
            sanitized_fn = Path(args.filename).stem if args.filename else None
            fn = f"{sanitized_fn}{tmpl.output_extension}" if sanitized_fn else f"{smal_tmpl.name}{smal_tmpl.output_extension}"
            out_filepath = args.output_dir / fn
            extra_context = tmpl.extra_context.copy()
            for ctx_key, compute_fn in tmpl.computed_extra_context.items():
                extra_context[ctx_key] = compute_fn(smal)
            try:
                generator.render_to_file(btmpl, smal, out_filepath, force=args.force, **extra_context)
                console.print(f"[green]Successfully generated debug boilerplate code: [bold cyan]{out_filepath}[/bold cyan][/green]")
            except ValueError:
                console.print(f"[red]Failed to render template {tmpl.name}.[/red]")
                raise


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
    start_timestamp = entries[0].timestamp_ms if entries else 0
    row_data = [
        [
            str(idx),
            (
                f"{entry.timestamp_ms}"
                f" (from_start=+{entry.timestamp_ms - start_timestamp}ms, from_prev=+{(f'{entry.timestamp_ms - entries[idx - 2].timestamp_ms}ms' if idx > 1 else 'null')})"
            ),
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
