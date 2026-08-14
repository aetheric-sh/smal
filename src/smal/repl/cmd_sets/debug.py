"""Module defining the `debug` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import TYPE_CHECKING, Any

import cmd2
from pydantic import BaseModel
from rich.markup import escape

from smal.codegen.code_generator import SMALCodeGenerator
from smal.codegen.templates.builtin_templates import TemplateRegistry
from smal.repl.cmd_sets.smal_cmd_set import SMALCmdSet
from smal.repl.helpers import echo_table, parse_key_value, parse_params
from smal.schemas.debug import SMALDebugEntry, SMALDebugEntryType
from smal.schemas.state_machine import SMALFile

if TYPE_CHECKING:
    import argparse

    from smal.repl.target_module import TargetModule
    from smal.schemas.state_machine import StateMachine

_debug_parser = cmd2.Cmd2ArgumentParser()
_debug_parser.add_subparsers(title="subcommand", help="subcommand help")

_run_parser = cmd2.Cmd2ArgumentParser()
_run_parser.add_argument(
    "-m",
    "--module",
    type=Path,
    completer=cmd2.Cmd.path_complete,
    help="Path to the external Python file containing the harvest function.",
)
_run_parser.add_argument(
    "-p",
    "--param",
    action="append",
    type=parse_key_value,
    help="Repeatable key=value pair (e.g., -p key1=value1 -p key2=value2) to pass additional parameters to the harvest function.",
)


class RunArgs(BaseModel):
    """Model describing the arguments to the run command."""

    module: Path | None = None
    param: list[tuple[str, Any]] | None = None


_boilerplate_parser = cmd2.Cmd2ArgumentParser()
_boilerplate_parser.add_argument("output_dir", type=Path, completer=cmd2.Cmd.path_complete, help="Directory to output the generated boilerplate code.")
_boilerplate_parser.add_argument("-l", "--lang", type=str, default="c", choices=["c"], help="Programming language for the boilerplate code.")
_boilerplate_parser.add_argument(
    "-f",
    "--filename",
    type=str,
    help="Optional filename for the generated boilerplate code. If not provided, a default name will be used.",
)
_boilerplate_parser.add_argument(
    "--force",
    action="store_true",
    help="Force overwrite of existing files in the output directory. If not set, existing files will not be overwritten.",
)


class BoilerplateArgs(BaseModel):
    """Model describing the arguments to the gen_boilerplate command."""

    output_dir: Path
    lang: str = "c"
    filename: str | None = None
    force: bool = False


class DebugCmdSet(SMALCmdSet):
    """Command set for debugging in the SMAL REPL."""

    @cmd2.with_argparser(_debug_parser)
    def do_debug(self, args: argparse.Namespace) -> None:
        """Manage SMAL state machine debugging.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        handler = getattr(args, "cmd2_subcommand_func", None)
        if handler is not None:
            handler(args)
        else:
            self._cmd.poutput("No subcommand given.")
            self._cmd.do_help("debug")

    @cmd2.as_subcommand_to("debug", "run", _run_parser, help="Run the SMAL debug data harvesting tool.")
    def debug_run(self, args: argparse.Namespace) -> None:
        """Run the SMAL debug data harvesting tool to harvest curated debug data from a connected device.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        Raises:
            RuntimeError: If the parent REPL application cannot be accessed or is not of the expected type.
            TypeError: If the harvest function does not match the expected signature.

        """
        parsed_args = RunArgs.model_validate(vars(args))
        parent_app = self.parent_app
        if parent_app.active_connection is None:
            parent_app.print_error("No active connection found. Please connect to a device first with the `connect` command.")
            return
        if parent_app.active_machine is None:
            parent_app.print_error("No active machine found. Please load a machine definition first with the `machine load` command.")
            return
        if parsed_args.module is not None:
            # An explicitly-provided module path takes precedence over any already-active module, so `-m` reliably
            # switches modules instead of being silently ignored whenever a module happens to already be active.
            parent_app.set_active_module(parsed_args.module)
            if parent_app.active_module is None:
                raise RuntimeError(f"Failed to set active module to {parsed_args.module}.")
            active_module: TargetModule = parent_app.active_module
            harvest_fn = active_module.harvest_fn
        elif parent_app.active_module is not None:
            harvest_fn = parent_app.active_module.harvest_fn
        else:
            parent_app.print_error(
                "No active module found. Please set a module first with the `module set` command or provide a module file path with the `--module` option.",
            )
            return
        parent_app.console.print(f"[bold blue] Harvesting data from machine '{parent_app.active_machine.name}'...[/bold blue]")
        extra_kwargs: dict[str, Any] = parse_params(parsed_args.param or [])
        try:
            raw_data = harvest_fn(parent_app.active_machine.name, parent_app.active_connection.device, **extra_kwargs)
        except Exception as e:  # noqa: BLE001 - Catching all exceptions to provide user feedback in the REPL.
            parent_app.print_error(f"Error during harvest function execution: {e}")
            return
        with parent_app.console.status(f"Deserializing debug entries: [bold cyan]{len(raw_data)} bytes[/bold cyan]"):
            try:
                entries = SMALDebugEntry.deserialize_entries_from_bytes(raw_data)
            except ValueError:
                parent_app.print_error("Failed to deserialize debug entries from the harvested data.")
                return
        parent_app.print_success(f"Successfully harvested and deserialized {len(entries)} debug entries.")
        parent_app.console.print()
        _display_entries(entries, parent_app.active_machine)

    @cmd2.as_subcommand_to("debug", "boilerplate", _boilerplate_parser, help="Generate boilerplate debugging code for a new project utilizing SMAL.")
    def debug_boilerplate(self, args: argparse.Namespace) -> None:
        """Generate boilerplate debugging code for a new project utilizing SMAL.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        Raises:
            RuntimeError: If the parent REPL application cannot be accessed or is not of the expected type.

        """
        parsed_args = BoilerplateArgs.model_validate(vars(args))
        parent_app = self.parent_app
        # Validate output directory existence and writability
        if not parsed_args.output_dir.exists():
            parsed_args.output_dir.mkdir(parents=True, exist_ok=True)
        elif not parsed_args.output_dir.is_dir():
            parent_app.print_error(f"Output path exists but is not a directory: {parsed_args.output_dir}")
            return
        generator = SMALCodeGenerator()
        smal = SMALFile.blank()
        boilerplate_templates = TemplateRegistry.get_dbg_boilerplate_templates(args.lang)
        if not boilerplate_templates:
            parent_app.print_error(f"No debug boilerplate templates found for language: {args.lang}")
            return
        for tmpl in boilerplate_templates:
            parent_app.console.print(f"Generating debug boilerplate code for [cyan]{args.lang}[/cyan] using template: [bold cyan]{tmpl.name}[/bold cyan]")
            _env, btmpl, smal_tmpl = generator.load_builtin_template(tmpl.name)
            sanitized_fn = Path(args.filename).stem if args.filename else None
            fn = f"{sanitized_fn}{tmpl.output_extension}" if sanitized_fn else f"{smal_tmpl.name}{smal_tmpl.output_extension}"
            out_filepath = args.output_dir / fn
            extra_context = tmpl.extra_context.copy()
            for ctx_key, compute_fn in tmpl.computed_extra_context.items():
                extra_context[ctx_key] = compute_fn(smal)
            try:
                generator.render_to_file(btmpl, smal, out_filepath, force=args.force, **extra_context)
                parent_app.print_success(f"Successfully generated debug boilerplate code: [bold cyan]{out_filepath}[/bold cyan]")
            except ValueError:
                parent_app.print_error(f"Failed to render template {tmpl.name}.")
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
                f" (from_start=+{entry.timestamp_ms - start_timestamp}ms, "
                f"from_prev=+{(f'{entry.timestamp_ms - entries[idx - 2].timestamp_ms}ms' if idx > 1 else 'null')})"
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
            "Details": {"style": "magenta"},
        },
    )
