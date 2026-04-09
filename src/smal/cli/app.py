"""Module defining the CLI interface for SMAL."""

from __future__ import annotations  # Until Python 3.14

from pathlib import Path  # noqa: TC003 - Move application import to TYPE_CHECKING block. Typer needs this.
from typing import Literal

import typer
from rich.console import Console

from smal.cli.commands.clean import clean_app
from smal.cli.commands.code import code_app
from smal.cli.commands.corrections import corrections_app
from smal.cli.commands.debug import debug_cmd
from smal.cli.commands.graphviz import graphviz_app
from smal.cli.commands.rules import rules_app
from smal.cli.commands.validate import validate_app
from smal.diagramming.generation import generate_state_machine_svg

app = typer.Typer(help="SMAL = State Machine Abstraction Language CLI")
app.add_typer(clean_app, name="clean")
app.add_typer(code_app, name="code")
app.add_typer(corrections_app, name="corrections")
# TODO: explain cmd
app.add_typer(graphviz_app, name="graphviz")
app.add_typer(rules_app, name="rules")
# TODO: simulate cmd
app.add_typer(validate_app, name="validate")


app.command("debug", help="Debug a SMAL state machine using custom debug data.")(debug_cmd)


@app.command("diagram", help="Generate a state machine diagram of your .smal file in .svg format.")
def diagram_root(
    smal_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to the input SMAL file."),  # noqa: B008 - Do not perform function call `typer.Argument` in argument defaults
    svg_output_dir: Path = typer.Argument(..., file_okay=False, dir_okay=True, writable=True, help="Directory where the generated SVG diagram will be written."),  # noqa: B008 - Do not perform function call `typer.Argument` in argument defaults
    open: bool = typer.Option(False, "--open", "-o", help="Open the generated SVG after creation."),  # noqa: A002 - Shadowing python builtin
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing SVG files if they already exist."),
    title: bool = typer.Option(True, "--title", "-t", help="Include the state machine title in the diagram."),
    orientation: Literal["LR", "TB"] = typer.Option("LR", "--orientation", "-r", help="The orientation of the diagram, either LR (Left-Right) or TB (Top-Bottom)"),
) -> None:
    """Generate a SVG diagram of a SMAL state machine.

    Args:
        smal_path (Path, optional): The path to the SMAL file.
        svg_output_dir (Path, optional): The directory where the generated SVG diagram will be written.
        open (bool, optional): Whether to open the generated SVG after creation. Defaults to False.
        force (bool, optional): Whether to overwrite existing SVG files if they already exist. Defaults to False.
        title (bool, optional): Whether to include the state machine title in the diagram. Defaults to True.
        orientation (Literal["LR", "TB"], optional): The orientation of the diagram, either LR (Left-Right) or TB (Top-Bottom). Defaults to "LR".

    """
    console = Console()
    if not svg_output_dir.exists():
        console.print(f"Created previously non-existent output directory for diagram: [bold cyan]{svg_output_dir}[/bold cyan]")
        svg_output_dir.mkdir(parents=True, exist_ok=True)
    with console.status(f"Generating state machine diagram for [cyan]{smal_path}[/cyan]", spinner="dots"):
        out_path = generate_state_machine_svg(smal_path, svg_output_dir, open=open, force=force, title=title, graph_attr={"rankdir": orientation})
    console.print(f"✅  [green]Diagram generated successfully: {out_path}[/green]")


if __name__ == "__main__":
    app()
