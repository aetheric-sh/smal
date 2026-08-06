"""Module defining the `diagram` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import TYPE_CHECKING, Literal

import cmd2
from pydantic import BaseModel

from smal.diagramming.generation import generate_state_machine_svg
from smal.repl.helpers import get_parent_app

if TYPE_CHECKING:
    import argparse


_diagram_parser = cmd2.Cmd2ArgumentParser()
_diagram_parser.add_argument("output_dir", type=Path, completer=cmd2.Cmd.path_complete, help="Directory to output the generated diagram.")
_diagram_parser.add_argument(
    "-m",
    "--machine",
    type=str,
    help="The name of the state machine to generate a diagram for, or a path to a SMAL file. If not provided, the active machine will be used.",
)
_diagram_parser.add_argument("-o", "--open", action="store_true", help="Open the generated diagram after creation.")
_diagram_parser.add_argument("-f", "--force", action="store_true", help="Force overwrite of existing files in the output directory.")
_diagram_parser.add_argument("-t", "--title", action="store_true", help="Include the state machine title in the diagram.")
_diagram_parser.add_argument("-r", "--orientation", choices=["lr", "tb"], default="lr", help="The orientation of the diagram, either lr (left-right) or tb (top-bottom).")


class DiagramArgs(BaseModel):
    """Model describing the arguments to the diagram command."""

    output_dir: Path
    machine: str | None = None
    open: bool = False
    force: bool = False
    title: bool = True
    orientation: Literal["lr", "tb"] = "lr"


class DiagramCmdSet(cmd2.CommandSet):
    """Command set for generating diagrams in the SMAL REPL."""

    @cmd2.with_argparser(_diagram_parser)
    def do_diagram(self, args: argparse.Namespace) -> None:
        """Generate a diagram of a SMAL state machine.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        Raises:
            RuntimeError: If the parent REPL application cannot be retrieved.

        """
        parsed_args = DiagramArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        console = parent_app.get_console()
        if parsed_args.machine is None:
            active_machine = parent_app.get_active_machine()
            if active_machine is None:
                parent_app.print_error("No active machine found. Please specify a loaded machine name or path to a SMAL file.")
                return
            smal_path = parent_app.get_machine_path(active_machine.name)
            if smal_path is None:
                parent_app.print_error(f"Could not find the path for the active machine: {active_machine.name}")
                return
        else:
            cached_path = parent_app.get_machine_path(parsed_args.machine)
            if cached_path is not None:
                smal_path = cached_path
            else:
                smal_path = Path(parsed_args.machine)
                if not smal_path.is_file():
                    parent_app.print_error(f"The specified machine name or path does not exist: {parsed_args.machine}")
                    return
        if not parsed_args.output_dir.exists():
            parsed_args.output_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"Created previously non-existent output directory for diagram: [bold cyan]{parsed_args.output_dir}[/bold cyan]")
        with console.status(f"Generating state machine diagram in [cyan]{parsed_args.output_dir}[/cyan]", spinner="dots"):
            out_path = generate_state_machine_svg(
                smal_path,
                parsed_args.output_dir,
                open=parsed_args.open,
                force=parsed_args.force,
                title=parsed_args.title,
                graph_attr={"rankdir": parsed_args.orientation.upper()},
            )
        parent_app.print_success(f"Diagram generated successfully: {out_path}", prefix="✅")
