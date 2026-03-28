from pathlib import Path

from rich.console import Console

from smal.codegen.code_generator import SMALCodeGenerator
from smal.schemas.smal_file import SMALFile


def generate_code_cmd(
    smal_path: Path,
    template: str | None = None,
    custom_template: Path | None = None,
    out_dir: Path = Path("./generated"),
    out_filename: str | None = None,
    force: bool = False,
) -> None:
    console = Console()
    if not smal_path.is_file():
        raise FileNotFoundError(f"SMAL file not found: {smal_path}")
    smal = SMALFile.from_file(smal_path)
    generator = SMALCodeGenerator()
    if custom_template and custom_template.is_file():
        with console.status(f"Generating code from {smal_path} using custom template {custom_template}", spinner="dots"):
            ctmpl = generator.load_external_template(custom_template)
            out_filepath = out_dir / (out_filename if out_filename else custom_template.stem)
            generator.render_to_file(ctmpl, smal, out_filepath, force=force)
    elif template:
        with console.status(f"Generating code from {smal_path} using built-in template '{template}'", spinner="dots"):
            btmpl, smal_tmpl = generator.load_builtin_template(template)
            out_filepath = out_dir / (out_filename if out_filename else f"{smal_tmpl.name}{smal_tmpl.output_extension}")
            generator.render_to_file(btmpl, smal, out_filepath, force=force)
    else:
        raise ValueError("Either a built-in template name or a custom template path must be provided.")
