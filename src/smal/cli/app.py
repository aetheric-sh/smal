import os
from pathlib import Path

import typer

from smal.cli.commands import generate_code_cmd_builtin, generate_diagram_cmd, install_graphviz_app
from smal.cli.commands.code import generate_code_cmd_custom
from smal.codegen.smal_templates import TemplateRegistry, is_valid_smal_template

app = typer.Typer(help="SMAL = State Machine Abstraction Language CLI")
app.add_typer(install_graphviz_app, name="install-graphviz")


@app.command(name="code", help="Generate code from a SMAL file using a standard or custom Jinja2 template.")
def code_cmd(
    smal_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to the input SMAL file."),
    builtin_template_name: str = typer.Option(
        None, "--template", "-t", help=f"Name of a built-in SMAL template to generate. Options: {', '.join(TemplateRegistry.list_template_names())}"
    ),
    custom_template_path: Path = typer.Option(
        None, "--custom", "-c", exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to a custom SMAL-compatible Jinja2 template file."
    ),
    out_dir: Path = typer.Option(
        Path("./generated"), "--out", "-o", file_okay=False, dir_okay=True, writable=True, help="Directory where generated code will be written (default: ./generated)."
    ),
    out_filename: str = typer.Option(
        None, "--filename", "-n", help="Optional filename for the generated code. If not provided, a default name based on the template will be used."
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files if they already exist."),
) -> None:
    # Ensure the SMAL file is real
    if not smal_path.is_file():
        raise typer.BadParameter(f"SMAL file not found: {smal_path}")
    # Enforce mutual exclusivity
    if (builtin_template_name is None) == (custom_template_path is None):
        raise typer.BadParameter("You must specify exactly one of --template or --custom.")
    # Validate output directory existence and writability
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
    elif not out_dir.is_dir():
        raise typer.BadParameter(f"Output path exists but is not a directory: {out_dir}")
    elif not os.access(out_dir, os.W_OK):
        raise typer.BadParameter(f"Output directory is not writable: {out_dir}")
    # If the user selected a builtin template
    if builtin_template_name:
        # Validate that the selected built-in template exists
        if not TemplateRegistry.has_template(builtin_template_name):
            raise typer.BadParameter(f"Unknown template '{builtin_template_name}'. Valid options: {', '.join(TemplateRegistry.list_template_names())}")
        # Generate the code using the built-in template
        generate_code_cmd_builtin(
            smal_path=smal_path,
            template_name=builtin_template_name,
            out_dir=out_dir,
            out_filename=out_filename,
            force=force,
        )
    # If the user selected a custom template
    elif custom_template_path:
        # Validate that the custom template file exists and is readable
        if not custom_template_path.is_file():
            raise typer.BadParameter(f"Custom template file not found: {custom_template_path}")
        if not os.access(custom_template_path, os.R_OK):
            raise typer.BadParameter(f"Custom template file is not readable: {custom_template_path}")
        # Validate that the custom template itself is a valid SMAL template by checking for required variables
        is_valid_tmpl, invalid_vars = is_valid_smal_template(custom_template_path)
        if not is_valid_tmpl:
            raise typer.BadParameter(f"Custom template {custom_template_path} is not a valid SMAL template. Invalid variables referenced: {', '.join(invalid_vars)}.")
        # Generate the custom code
        generate_code_cmd_custom(
            smal_path=smal_path,
            custom_template_path=custom_template_path,
            out_dir=out_dir,
            out_filename=out_filename,
            force=force,
        )
    # This should never happen due to the mutual exclusivity check above, but we include it for completeness
    else:
        raise typer.BadParameter("Invalid template configuration. This should never happen due to earlier validation.")


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


if __name__ == "__main__":
    app()
