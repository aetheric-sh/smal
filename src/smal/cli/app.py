from pathlib import Path

import typer

from smal.cli.commands import generate_code_cmd, generate_diagram_cmd, install_graphviz_app
from smal.codegen.smal_templates import TemplateRegistry

app = typer.Typer(help="SMAL = State Machine Abstraction Language CLI")
app.add_typer(install_graphviz_app, name="install-graphviz")


@app.command(name="code", help="Generate code from a SMAL file using a standard or custom Jinja2 template.")
def code_cmd(
    smal_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to the input SMAL file."),
    template: str = typer.Option(None, "--template", "-t", help=f"Name of a built-in SMAL template to generate. Options: {', '.join(STANDARD_TEMPLATES)}"),
    custom_template: Path = typer.Option(
        None, "--custom", "-c", exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to a custom SMAL-compatible Jinja2 template file."
    ),
    out_dir: Path = typer.Option(
        Path("./generated"), "--out", "-o", file_okay=False, dir_okay=True, writable=True, help="Directory where generated code will be written (default: ./generated)."
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files if they already exist."),
) -> None:
    # Enforce mutual exclusivity
    if (template is None) == (custom_template is None):
        raise typer.BadParameter("You must specify exactly one of --template or --custom.")

    # Validate built-in template name
    if template and not TemplateRegistry.has_template(template):
        raise typer.BadParameter(f"Unknown template '{template}'. Valid options: {', '.join(TemplateRegistry.list_template_names())}")

    generate_code_cmd(
        smal_path=smal_path,
        template=template,
        custom_template=custom_template,
        out_dir=out_dir,
        force=force,
    )


@app.command(name="diagram", help="Generate an SVG state machine diagram from a SMAL file.")
def diagram_cmd(
    smal_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to the input SMAL file."),
    svg_output_dir: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, writable=True, help="Directory where the generated SVG diagram will be written."),
    open: bool = typer.Option(False, "--open", "-o", help="Open the generated SVG after creation."),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing SVG files if they already exist."),
    title: bool = typer.Option(True, "--title", "-t", help="Include the state machine title in the diagram."),
) -> None:
    generate_diagram_cmd(
        smal_path=smal_path,
        svg_output_dir=svg_output_dir,
        open=open,
        force=force,
        title=title,
    )
