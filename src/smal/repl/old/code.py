# """Module defining the code CLI command for generating code from SMAL files using Jinja2 templates."""

# from __future__ import annotations  # Until Python 3.14

# import os
# from pathlib import Path

# import typer
# from rich.console import Console

# from smal.cli.commands.helpers import echo_table
# from smal.cli.commands.validate import JinjaTemplateValidator
# from smal.codegen import MacroRegistry, TemplateRegistry
# from smal.codegen.code_generator import SMALCodeGenerator
# from smal.schemas.state_machine import SMALFile

# code_app = typer.Typer(help="Generate code from SMAL files using Jinja2 templates.", no_args_is_help=True)


# @code_app.command("generate", help="Generate code from a SMAL file using a Jinja2 template.", no_args_is_help=True)
# def generate_cmd(
#     smal_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to the input SMAL file."),  # noqa: B008
#     template: str = typer.Option(
#         None,
#         "--template",
#         "-t",
#         help="Name of the builtin SMAL template to generate, or the filepath to a custom, SMAL-compliant Jinja2 template to generate.",
#     ),
#     out_dir: Path = typer.Option(  # noqa: B008
#         Path("./generated"),
#         "--out",
#         "-o",
#         file_okay=False,
#         dir_okay=True,
#         writable=True,
#         help="Directory where generated code will be written (default: ./generated).",
#     ),
#     out_filename: str = typer.Option(
#         None,
#         "--filename",
#         "-n",
#         help="Optional filename for the generated code. If not provided, a default name based on the template will be used.",
#     ),
#     force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files if they already exist."),
# ) -> None:
#     """Generate code from a SMAL file using a Jinja2 template.

#     Args:
#         smal_path (Path, optional): The path to the input SMAL file.
#         template (str, optional): The name of the builtin SMAL template to generate, or the filepath to a custom, SMAL-compliant Jinja2 template to generate.
#         out_dir (Path, optional): The directory where generated code will be written. Defaults to Path("./generated").
#         out_filename (str, optional): The optional filename for the generated code. If not provided, a default name based on the template will be used. Defaults to None.
#         force (bool, optional): Whether to overwrite existing files if they already exist. Defaults to False.

#     Raises:
#         typer.BadParameter: If the provided template name is not a builtin template and is not a valid filepath to a custom template.
#         typer.BadParameter: If the provided custom template file is not a valid SMAL-compliant Jinja2 template. See the error report for details.
#         typer.BadParameter: If the output directory exists but is not a directory.
#         typer.BadParameter: If the output directory is not writable.

#     """
#     console = Console()
#     # Validate output directory existence and writability
#     if not out_dir.exists():
#         out_dir.mkdir(parents=True, exist_ok=True)
#     elif not out_dir.is_dir():
#         raise typer.BadParameter(f"Output path exists but is not a directory: {out_dir}")
#     # If the user selected a builtin template
#     if TemplateRegistry.has_template(template):
#         # Generate the code using the built-in template
#         try:
#             with console.status(f"Generating code from {smal_path} using built-in template: [bold cyan]{template}[/bold cyan]", spinner="dots"):
#                 generated_filepath = generate_code_cmd_builtin(
#                     smal_path=smal_path,
#                     template_name=template,
#                     out_dir=out_dir,
#                     out_filename=out_filename,
#                     force=force,
#                 )
#             console.print(f"[green]Code successfully generated from builtin template {template}: [bold cyan]{generated_filepath}[/bold cyan][/green]")
#         except ValueError as e:
#             console.print(f"[red]Failed to generate code from builtin template {template} due to rendering error: {e}[/red]")
#     # If the user selected a custom template
#     else:
#         custom_template_path = Path(template)
#         # Validate that the custom template file exists and is readable
#         if not custom_template_path.is_file():
#             raise typer.BadParameter(f"Custom template file not found: {custom_template_path}")
#         if not os.access(custom_template_path, os.R_OK):
#             raise typer.BadParameter(f"Custom template file is not readable: {custom_template_path}")
#         # Validate that the custom template itself is a valid SMAL template by checking for required variables
#         validator = JinjaTemplateValidator(custom_template_path)
#         res = validator.validate()
#         if not res.ok:
#             res.echo_report()
#             raise typer.BadParameter(f"Custom template {custom_template_path} is not a valid SMAL template. See above report for details.")
#         # Generate the custom code
#         try:
#             with console.status(f"Generating code from {smal_path} using custom template: [bold cyan]{custom_template_path}[/bold cyan]", spinner="dots"):
#                 generated_filepath = generate_code_cmd_custom(
#                     smal_path=smal_path,
#                     custom_template_path=custom_template_path,
#                     out_dir=out_dir,
#                     out_filename=out_filename,
#                     force=force,
#                 )
#             console.print(
#                 f"[green]Code successfully generated from custom template [bold yellow]{custom_template_path.name}[/bold yellow]:"
#                 f" [bold cyan]{generated_filepath}[/bold cyan][/green]",
#             )
#         except ValueError as e:
#             console.print(f"[red]Failed to generate code from custom template {custom_template_path} due to rendering error: {e}[/red]")


# @code_app.command("macros", help="List all Jinja2 macros provided by SMAL that are usable by external templates.")
# def macros_cmd() -> None:
#     """List all builtin jinja2 macros provided by SMAL."""
#     echo_table(
#         "Builtin SMAL Macros",
#         ["Name", "Lang", "Import Path", "Signature", "Description"],
#         [[macro.name, macro.lang, macro.import_path, macro.signature, macro.description] for macro in MacroRegistry.list_macros()],
#     )


# @code_app.command("templates", help="List all Jinja2 templates provided by SMAL that can be used to generate code.")
# def templates_cmd() -> None:
#     """List all builtin jinja2 templates provided by SMAL."""
#     echo_table("Builtin SMAL Templates", ["Name", "Lang", "Description"], [[template.name, template.lang, template.description] for template in TemplateRegistry.list_templates()])


# def generate_code_cmd_builtin(smal_path: Path, template_name: str, out_dir: Path, out_filename: str | None, force: bool) -> Path:
#     """Generate code using a builtin SMAL jinja template.

#     Args:
#         smal_path (Path): The path to the SMAL file.
#         template_name (str): The name of the builtin SMAL template to use for code generation.
#         out_dir (Path): The directory where the generated code will be written.
#         out_filename (str | None): The optional filename for the generated code. If not provided, a default name based on the template will be used.
#         force (bool): Whether to overwrite existing files if they already exist.

#     Returns:
#         Path: The path to the generated code file.

#     """
#     smal = SMALFile.from_file(smal_path)
#     generator = SMALCodeGenerator()
#     _env, btmpl, smal_tmpl = generator.load_builtin_template(template_name)
#     sanitized_out_fn = Path(out_filename).stem if out_filename else None
#     fn = f"{sanitized_out_fn}{smal_tmpl.output_extension}" if sanitized_out_fn else f"{smal_tmpl.name}{smal_tmpl.output_extension}"
#     out_filepath = out_dir / fn
#     extra_context = smal_tmpl.extra_context.copy()
#     for ctx_key, compute_fn in smal_tmpl.computed_extra_context.items():
#         extra_context[ctx_key] = compute_fn(smal)
#     try:
#         generator.render_to_file(btmpl, smal, out_filepath, force=force, **extra_context)
#     except ValueError:  # noqa: TRY203 - Error will automatically re-raise. Keeping for clarity
#         raise
#     return out_filepath


# def generate_code_cmd_custom(smal_path: Path, custom_template_path: Path, out_dir: Path, out_filename: str | None, force: bool) -> Path:
#     """Generate code using a custom jinja template.

#     Args:
#         smal_path (Path): The path to the SMAL file.
#         custom_template_path (Path): The path to the custom, SMAL-compliant Jinja2 template file to use for code generation.
#         out_dir (Path): The directory where the generated code will be written.
#         out_filename (str | None): The optional filename for the generated code. If not provided, a default name based on the template will be used.
#         force (bool): Whether to overwrite existing files if they already exist.

#     Returns:
#         Path: The path to the generated code file.

#     """
#     smal = SMALFile.from_file(smal_path)
#     generator = SMALCodeGenerator()
#     _env, ctmpl = generator.load_external_template(custom_template_path)
#     sanitized_out_fn = Path(out_filename).stem if out_filename else None
#     fn = f"{sanitized_out_fn}{ctmpl.output_extension}" if sanitized_out_fn else f"{ctmpl.name}{ctmpl.output_extension}"
#     out_filepath = out_dir / fn
#     try:
#         generator.render_to_file(ctmpl, smal, out_filepath, force=force)
#     except ValueError:  # noqa: TRY203 - Error will automatically re-raise. Keeping for clarity
#         raise
#     return out_filepath
