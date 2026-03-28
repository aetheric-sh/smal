from pathlib import Path

from rich.console import Console

from smal.codegen.code_generator import SMALCodeGenerator
from smal.schemas.smal_file import SMALFile


def generate_code_cmd_builtin(smal_path: Path, template_name: str, out_dir: Path, out_filename: str | None, force: bool) -> None:
    console = Console()
    smal = SMALFile.from_file(smal_path)
    generator = SMALCodeGenerator()
    with console.status(f"Generating code from {smal_path} using built-in template '{template_name}'", spinner="dots"):
        btmpl, smal_tmpl = generator.load_builtin_template(template_name)
        out_filepath = out_dir / (out_filename if out_filename else f"{smal_tmpl.name}{smal_tmpl.output_extension}")
        extra_context = smal_tmpl.extra_context.copy()
        for ctx_key, compute_fn in smal_tmpl.computed_extra_context.items():
            extra_context[ctx_key] = compute_fn(smal)
        generator.render_to_file(btmpl, smal, out_filepath, force=force, **extra_context)


def generate_code_cmd_custom(smal_path: Path, custom_template_path: Path, out_dir: Path, out_filename: str | None, force: bool) -> None:
    console = Console()
    smal = SMALFile.from_file(smal_path)
    generator = SMALCodeGenerator()
    with console.status(f"Generating code from {smal_path} using custom template {custom_template_path}", spinner="dots"):
        ctmpl = generator.load_external_template(custom_template_path)
        out_filepath = out_dir / (out_filename if out_filename else custom_template_path.stem)
        generator.render_to_file(ctmpl, smal, out_filepath, force=force)
