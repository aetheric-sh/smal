from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import Literal

import typer
from rich.console import Console

from smal.cli.commands import code_app, graphviz_app, rules_app, validate_app
from smal.diagramming.generation import generate_state_machine_svg

app = typer.Typer(help="SMAL = State Machine Abstraction Language CLI")
app.add_typer(code_app, name="code")
app.add_typer(graphviz_app, name="graphviz")
app.add_typer(rules_app, name="rules")
app.add_typer(validate_app, name="validate")


@app.command("diagram", help="Generate a state machine diagram of your .smal file in .svg format.")
def diagram_root(
    smal_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to the input SMAL file."),
    svg_output_dir: Path = typer.Argument(..., file_okay=False, dir_okay=True, writable=True, help="Directory where the generated SVG diagram will be written."),
    open: bool = typer.Option(False, "--open", "-o", help="Open the generated SVG after creation."),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing SVG files if they already exist."),
    title: bool = typer.Option(True, "--title", "-t", help="Include the state machine title in the diagram."),
    orientation: Literal["LR", "TB"] = typer.Option("LR", "--orientation", "-r", help="The orientation of the diagram, either LR (Left-Right) or TB (Top-Bottom)"),
) -> None:
    console = Console()
    if not svg_output_dir.exists():
        console.print(f"Created previously non-existent output directory for diagram: [bold cyan]{svg_output_dir}[/bold cyan]")
        svg_output_dir.mkdir(parents=True, exist_ok=True)
    with console.status(f"Generating state machine diagram for [cyan]{smal_path}[/cyan]", spinner="dots"):
        out_path = generate_state_machine_svg(smal_path, svg_output_dir, open=open, force=force, title=title, graph_attr={"rankdir": orientation})
    console.print(f"✅  [green]Diagram generated successfully: {out_path}[/green]")


if __name__ == "__main__":
    app()
