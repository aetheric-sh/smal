"""Module defining the `code` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

import os
from pathlib import Path
from typing import TYPE_CHECKING

import cmd2
from pydantic import BaseModel

from smal.codegen import MacroRegistry, TemplateRegistry
from smal.codegen.code_generator import SMALCodeGenerator
from smal.repl.cmd_sets.smal_cmd_set import SMALCmdSet
from smal.repl.cmd_sets.validate import JinjaTemplateValidator
from smal.repl.completers import machine_completer, template_completer
from smal.repl.helpers import echo_table, get_persistence
from smal.schemas.state_machine import SMALFile

if TYPE_CHECKING:
    import argparse

_code_parser = cmd2.Cmd2ArgumentParser()
_code_parser.add_subparsers(title="subcommand", help="subcommand help")
_generate_parser = cmd2.Cmd2ArgumentParser()
_generate_parser.add_argument(
    "template",
    type=str,
    completer=template_completer,
    help="Name of the builtin SMAL template to generate, or the filepath to a custom, SMAL-compliant Jinja2 template to generate.",
)
_generate_parser.add_argument(
    "-m",
    "--machine",
    type=str,
    completer=machine_completer,
    default=None,
    help="Name of the SMAL state machine to generate code for, or a path to the SMAL file. If not provided, the active machine will be used.",
)
_generate_parser.add_argument(
    "-o",
    "--output-dir",
    type=Path,
    default=Path("./generated"),
    help="Directory to output the generated code (default: ./generated).",
)
_generate_parser.add_argument(
    "-n",
    "--filename",
    type=str,
    default=None,
    help="Optional filename for the generated code. If not provided, a default name will be used.",
)
_generate_parser.add_argument(
    "--force",
    action="store_true",
    help="Force overwrite of existing files in the output directory. If not set, existing files will not be overwritten.",
)


class GenerateArgs(BaseModel):
    """Arguments for the `code generate` command."""

    template: str
    machine: str | None = None
    output_dir: Path = Path("./generated")
    filename: str | None = None
    force: bool = False


_macros_parser = cmd2.Cmd2ArgumentParser()
_templates_parser = cmd2.Cmd2ArgumentParser()


class CodeCmdSet(SMALCmdSet):
    """Command set for handling code in the SMAL REPL."""

    @cmd2.with_argparser(_code_parser)
    def do_code(self, args: argparse.Namespace) -> None:
        """Manage SMAL state machine code generation.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        handler = args.cmd2_handler.get()
        if handler is not None:
            handler(args)
        else:
            self._cmd.poutput("No subcommand given.")
            self._cmd.do_help("code")

    @cmd2.as_subcommand_to("code", "generate", _generate_parser, help="Generate code from a SMAL file using a Jinja2 template.")
    def code_generate(self, args: argparse.Namespace) -> None:
        """Generate code from a SMAL file using a Jinja2 template.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = GenerateArgs.model_validate(vars(args))
        parent_app = self.parent_app
        console = parent_app.get_console()
        persistence = get_persistence()
        # Validate output directory existence and writability
        if not parsed_args.output_dir.exists():
            parsed_args.output_dir.mkdir(parents=True, exist_ok=True)
        elif not parsed_args.output_dir.is_dir():
            parent_app.print_error(f"Output path exists but is not a directory: {parsed_args.output_dir}")
            return
        if parsed_args.machine is None:
            active_machine = parent_app.get_active_machine()
            if active_machine is None:
                parent_app.print_error("No active machine found. Please specify a machine or set an active machine.")
                return
            machine = active_machine
        else:
            cached_machine = persistence.machines.get(parsed_args.machine)
            if cached_machine is None:
                cached_path = persistence.machine_paths.get(parsed_args.machine)
                if cached_path is None:
                    parent_app.print_error(f"Specified machine is not cached and no path is known: {parsed_args.machine}")
                    return
                cached_machine = SMALFile.from_file(cached_path)
            machine = cached_machine
        # If the user selected a builtin template
        if TemplateRegistry.has_template(parsed_args.template):
            # Generate the code using the built-in template
            try:
                with console.status(
                    f"Generating code from {machine.name} using built-in template: [bold cyan]{parsed_args.template}[/bold cyan]",
                    spinner="dots",
                ):
                    generated_filepath = generate_code_cmd_builtin(
                        machine=machine,
                        template_name=parsed_args.template,
                        out_dir=parsed_args.output_dir,
                        out_filename=parsed_args.filename,
                        force=parsed_args.force,
                    )
                console.print(
                    f"[green]Code successfully generated from builtin template {parsed_args.template}: [bold cyan]{generated_filepath}[/bold cyan][/green]",
                )
            except ValueError as e:
                console.print(f"[red]Failed to generate code from builtin template {parsed_args.template} due to rendering error: {e}[/red]")
        # If the user selected a custom template
        else:
            custom_template_path = Path(parsed_args.template)
            # Validate that the custom template file exists and is readable
            if not custom_template_path.is_file():
                parent_app.print_error(f"Custom template file not found: {custom_template_path}")
                return
            if not os.access(custom_template_path, os.R_OK):
                parent_app.print_error(f"Custom template file is not readable: {custom_template_path}")
                return
            # Validate that the custom template itself is a valid SMAL template by checking for required variables
            validator = JinjaTemplateValidator(custom_template_path)
            res = validator.validate()
            if not res.ok:
                res.echo_report()
                parent_app.print_error(f"Custom template {custom_template_path} is not a valid SMAL template. See above report for details.")
                return
            # Generate the custom code
            try:
                with console.status(
                    f"Generating code from {machine.name} using custom template: [bold cyan]{custom_template_path}[/bold cyan]", spinner="dots"
                ):
                    generated_filepath = generate_code_cmd_custom(
                        machine=machine,
                        custom_template_path=custom_template_path,
                        out_dir=parsed_args.output_dir,
                        out_filename=parsed_args.filename,
                        force=parsed_args.force,
                    )
                console.print(
                    f"[green]Code successfully generated from custom template [bold yellow]{custom_template_path.name}[/bold yellow]:"
                    f" [bold cyan]{generated_filepath}[/bold cyan][/green]",
                )
            except ValueError as e:
                console.print(f"[red]Failed to generate code from custom template {custom_template_path} due to rendering error: {e}[/red]")

    @cmd2.as_subcommand_to("code", "macros", _macros_parser, help="List all Jinja2 macros provided by SMAL that are usable by external templates.")
    def code_macros(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused argument
        """List all Jinja2 macros provided by SMAL that are usable by external templates.

        Args:
            args (argparse.Namespace): The parsed command-line arguments. Unused.

        """
        echo_table(
            "Builtin SMAL Macros",
            ["Name", "Lang", "Import Path", "Signature", "Description"],
            [[macro.name, macro.lang, macro.import_path, macro.signature, macro.description] for macro in MacroRegistry.list_macros()],
            col_metadata={
                "Name": {"style": "cyan"},
                "Lang": {"style": "green"},
                "Import Path": {"style": "yellow"},
                "Signature": {"style": "magenta"},
                "Description": {"style": "white"},
            },
        )

    @cmd2.as_subcommand_to("code", "templates", _templates_parser, help="List all Jinja2 templates provided by SMAL that can be used to generate code.")
    def code_templates(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused argument
        """List all Jinja2 templates provided by SMAL that can be used to generate code.

        Args:
            args (argparse.Namespace): The parsed command-line arguments. Unused.

        """
        echo_table(
            "Builtin SMAL Templates",
            ["Name", "Lang", "Description"],
            [[template.name, template.lang, template.description] for template in TemplateRegistry.list_templates()],
            col_metadata={
                "Name": {"style": "cyan"},
                "Lang": {"style": "green"},
                "Description": {"style": "yellow"},
            },
        )


def generate_code_cmd_builtin(machine: SMALFile, template_name: str, out_dir: Path, out_filename: str | None, force: bool) -> Path:
    """Generate code using a builtin SMAL jinja template.

    Args:
        machine (SMALFile): The SMAL machine object.
        template_name (str): The name of the builtin SMAL template to use for code generation.
        out_dir (Path): The directory where the generated code will be written.
        out_filename (str | None): The optional filename for the generated code. If not provided, a default name based on the template will be used.
        force (bool): Whether to overwrite existing files if they already exist.

    Returns:
        Path: The path to the generated code file.

    """
    generator = SMALCodeGenerator()
    _env, btmpl, smal_tmpl = generator.load_builtin_template(template_name)
    sanitized_out_fn = Path(out_filename).stem if out_filename else None
    fn = f"{sanitized_out_fn}{smal_tmpl.output_extension}" if sanitized_out_fn else f"{smal_tmpl.name}{smal_tmpl.output_extension}"
    out_filepath = out_dir / fn
    extra_context = smal_tmpl.extra_context.copy()
    for ctx_key, compute_fn in smal_tmpl.computed_extra_context.items():
        extra_context[ctx_key] = compute_fn(machine)
    try:
        generator.render_to_file(btmpl, machine, out_filepath, force=force, **extra_context)
    except ValueError:  # noqa: TRY203 - Error will automatically re-raise. Keeping for clarity
        raise
    return out_filepath


def generate_code_cmd_custom(machine: SMALFile, custom_template_path: Path, out_dir: Path, out_filename: str | None, force: bool) -> Path:
    """Generate code using a custom jinja template.

    Args:
        machine (SMALFile): The SMAL machine object.
        custom_template_path (Path): The path to the custom, SMAL-compliant Jinja2 template file to use for code generation.
        out_dir (Path): The directory where the generated code will be written.
        out_filename (str | None): The optional filename for the generated code. If not provided, a default name based on the template will be used.
        force (bool): Whether to overwrite existing files if they already exist.

    Returns:
        Path: The path to the generated code file.

    """
    generator = SMALCodeGenerator()
    _env, ctmpl = generator.load_external_template(custom_template_path)
    sanitized_out_fn = Path(out_filename).stem if out_filename else None
    fn = f"{sanitized_out_fn}{ctmpl.output_extension}" if sanitized_out_fn else f"{ctmpl.name}{ctmpl.output_extension}"
    out_filepath = out_dir / fn
    try:
        generator.render_to_file(ctmpl, machine, out_filepath, force=force)
    except ValueError:  # noqa: TRY203 - Error will automatically re-raise. Keeping for clarity
        raise
    return out_filepath
