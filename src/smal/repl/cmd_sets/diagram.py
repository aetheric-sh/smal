"""Module defining the `diagram` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

import os
import platform
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import cmd2
import yaml
from pydantic import BaseModel

from smal.diagramming.mermaid import render_mermaid_markdown
from smal.repl.cmd_sets.smal_cmd_set import SMALCmdSet
from smal.repl.completers import machine_completer
from smal.repl.helpers import get_persistence
from smal.schemas.machine import Machine

if TYPE_CHECKING:
    import argparse


_diagram_parser = cmd2.Cmd2ArgumentParser()
_diagram_parser.add_argument("output_dir", type=Path, completer=cmd2.Cmd.path_complete, help="Directory to output the generated diagram.")
_diagram_parser.add_argument(
    "-m",
    "--machine",
    type=str,
    completer=machine_completer,
    help="The name of the state machine to generate a diagram for, or a path to a SMAL file. If not provided, the active machine will be used.",
)
_diagram_parser.add_argument("-o", "--open", action="store_true", help="Open the generated diagram after creation.")
_diagram_parser.add_argument("-f", "--force", action="store_true", help="Force overwrite of existing files in the output directory.")
_diagram_parser.add_argument("-t", "--title", action="store_true", help="Include the state machine title in the diagram.")
_diagram_parser.add_argument(
    "-r",
    "--orientation",
    choices=["lr", "tb"],
    default="lr",
    help="The orientation of the diagram, either lr (left-right) or tb (top-bottom).",
)


class DiagramArgs(BaseModel):
    """Model describing the arguments to the diagram command."""

    output_dir: Path
    machine: str | None = None
    open: bool = False
    force: bool = False
    title: bool = False
    orientation: Literal["lr", "tb"] = "lr"


class DiagramCmdSet(SMALCmdSet):
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
        parent_app = self.parent_app
        persistence = get_persistence()
        if parsed_args.machine is None:
            if parent_app.active_machine is None:
                parent_app.print_error("No active machine found. Please specify a loaded machine name or path to a SMAL file.")
                return
            smal_path = persistence.machine_paths.get(parent_app.active_machine.name)
            if smal_path is None:
                parent_app.print_error(f"Could not find the path for the active machine: {parent_app.active_machine.name}")
                return
        else:
            cached_path = persistence.machine_paths.get(parsed_args.machine)
            if cached_path is not None:
                smal_path = cached_path
            else:
                smal_path = Path(parsed_args.machine)
                if not smal_path.is_file():
                    parent_app.print_error(f"The specified machine name or path does not exist: {parsed_args.machine}")
                    return
        machine = Machine.from_file(smal_path)
        out_path = parsed_args.output_dir / f"{machine.name}_diagram.md".lower()
        try:
            with parent_app.console.status(f"Generating state machine diagram in [cyan]{parsed_args.output_dir}[/cyan]", spinner="dots"):
                markdown = render_mermaid_markdown(
                    machine,
                    direction="LR" if parsed_args.orientation == "lr" else "TB",
                    title=machine.name if parsed_args.title else "",
                    theme="dark",
                )
                parsed_args.output_dir.mkdir(parents=True, exist_ok=True)
                with out_path.open("w" if parsed_args.force else "x", encoding="utf-8") as output:
                    output.write(markdown)
        except FileExistsError as e:
            parent_app.print_error(f"Could not create the diagram. Use --force to replace an existing diagram file. {e}")
            return
        except (OSError, ValueError, TypeError, yaml.YAMLError) as e:
            parent_app.print_error(f"Failed to generate diagram from {smal_path}: {e}")
            return
        parent_app.print_success(f"Diagram generated successfully: {out_path}", prefix="✅")
        if parsed_args.open:
            try:
                absolute_path = out_path.resolve()
                system = platform.system()
                if system == "Windows":
                    os.startfile(absolute_path)  # noqa: S606 - Open the generated Markdown document.
                else:
                    subprocess.run(["open" if system == "Darwin" else "xdg-open", str(absolute_path)], check=True)
            except (OSError, subprocess.CalledProcessError) as e:
                parent_app.print_error(f"Failed to open diagram {out_path}: {e}")
