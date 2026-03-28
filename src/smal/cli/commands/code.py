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
    if custom_template and custom_template.is_file():
        with console.status(f"Generating code from {smal_path} using custom template {custom_template}", spinner="dots"):
            template_dir = custom_template.parent
            generator = SMALCodeGenerator(template_dir)
            template_name = custom_template.name
            generator.render_to_file(template_name, smal, out_dir / template_name, force=force)
    elif template:
        with console.status(f"Generating code from {smal_path} using built-in template '{template}'", spinner="dots"):
            generator = SMALCodeGenerator()
            generator.render_to_file(template, smal, out_dir / template, force=force)
    else:
        raise ValueError("Either a built-in template name or a custom template path must be provided.")
