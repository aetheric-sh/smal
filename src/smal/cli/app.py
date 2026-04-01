from __future__ import annotations  # Until Python 3.14

import os
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console

from smal.cli.commands import generate_code_cmd_builtin, generate_diagram_cmd, install_graphviz_app, rules_app
from smal.cli.commands.code import generate_code_cmd_custom
from smal.cli.commands.helpers import echo_table
from smal.cli.commands.validate import JinjaTemplateValidator
from smal.codegen.smal_templates import TemplateRegistry

app = typer.Typer(help="SMAL = State Machine Abstraction Language CLI")
app.add_typer(install_graphviz_app, name="graphviz")
app.add_typer(rules_app, name="rules")
console = Console()


@app.command(name="templates", help="Get a manifest of all provided code generation templates SMAL provides.")
def templates_cmd() -> None:
    echo_table("SMAL Builtin Codegen Templates", ["Name", "Lang", "Description"], [[tmpl.name, tmpl.lang, tmpl.description] for tmpl in TemplateRegistry.list_templates()])


@app.command(name="code", help="Generate code from a SMAL file using a standard or custom Jinja2 template.")
def code_cmd(
    smal_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to the input SMAL file."),
    template: str = typer.Option(
        None,
        "--template",
        "-t",
        help="Name of the builtin SMAL template to generate, or the filepath to a custom, SMAL-compliant Jinja2 template to generate.",
    ),
    out_dir: Path = typer.Option(
        Path("./generated"),
        "--out",
        "-o",
        file_okay=False,
        dir_okay=True,
        writable=True,
        help="Directory where generated code will be written (default: ./generated).",
    ),
    out_filename: str = typer.Option(
        None,
        "--filename",
        "-n",
        help="Optional filename for the generated code. If not provided, a default name based on the template will be used.",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files if they already exist."),
) -> None:
    # Validate output directory existence and writability
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
    elif not out_dir.is_dir():
        raise typer.BadParameter(f"Output path exists but is not a directory: {out_dir}")
    # If the user selected a builtin template
    if TemplateRegistry.has_template(template):
        # Generate the code using the built-in template
        with console.status(f"Generating code from {smal_path} using built-in template: [bold cyan]{template}[/bold cyan]", spinner="dots"):
            generated_filepath = generate_code_cmd_builtin(
                smal_path=smal_path,
                template_name=template,
                out_dir=out_dir,
                out_filename=out_filename,
                force=force,
            )
        console.print(f"[green]Code successfully generated from builtin template {template}: [bold cyan]{generated_filepath}[/bold cyan][/green]")
    # If the user selected a custom template
    else:
        custom_template_path = Path(template)
        # Validate that the custom template file exists and is readable
        if not custom_template_path.is_file():
            raise typer.BadParameter(f"Custom template file not found: {custom_template_path}")
        if not os.access(custom_template_path, os.R_OK):
            raise typer.BadParameter(f"Custom template file is not readable: {custom_template_path}")
        # Validate that the custom template itself is a valid SMAL template by checking for required variables
        validator = JinjaTemplateValidator(custom_template_path)
        res = validator.validate()
        if not res.ok:
            res.echo_report()
            raise typer.BadParameter(f"Custom template {custom_template_path} is not a valid SMAL template. See above report for details.")
        # Generate the custom code
        with console.status(f"Generating code from {smal_path} using custom template: [bold cyan]{custom_template_path}[/bold cyan]", spinner="dots"):
            generated_filepath = generate_code_cmd_custom(
                smal_path=smal_path,
                custom_template_path=custom_template_path,
                out_dir=out_dir,
                out_filename=out_filename,
                force=force,
            )
        console.print(
            f"[green]Code successfully generated from custom template [bold yellow]{custom_template_path.name}[/bold yellow]: [bold cyan]{generated_filepath}[/bold cyan][/green]",
        )


@app.command(name="diagram", help="Generate an SVG state machine diagram from a SMAL file.")
def diagram_cmd(
    smal_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to the input SMAL file."),
    svg_output_dir: Path = typer.Argument(..., file_okay=False, dir_okay=True, writable=True, help="Directory where the generated SVG diagram will be written."),
    open: bool = typer.Option(False, "--open", "-o", help="Open the generated SVG after creation."),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing SVG files if they already exist."),
    title: bool = typer.Option(True, "--title", "-t", help="Include the state machine title in the diagram."),
    orientation: Literal["LR", "TB"] = typer.Option("LR", "--orientation", "-r", help="The orientation of the diagram, either LR (Left-Right) or TB (Top-Bottom)"),
) -> None:
    if not svg_output_dir.exists():
        console.print(f"Created previously non-existent output directory for diagram: [bold cyan]{svg_output_dir}[/bold cyan]")
        svg_output_dir.mkdir(parents=True, exist_ok=True)
    generate_diagram_cmd(smal_path=smal_path, svg_output_dir=svg_output_dir, open=open, force=force, title=title, orientation=orientation)


@app.command(name="validate", help="Validate a custom Jinja2 template for use with SMAL code generation by checking for undefined variables and missing macro templates.")
def validate_cmd(
    template_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to the Jinja2 template file."),
) -> None:
    validator = JinjaTemplateValidator(template_path)
    validation_result = validator.validate()
    validation_result.echo_report(template_path)


if __name__ == "__main__":
    app()
