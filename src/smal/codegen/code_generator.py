from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, PackageLoader, Template, select_autoescape

from smal.codegen.smal_templates import SMALTemplate, TemplateRegistry
from smal.schemas.smal_file import SMALFile


class SMALCodeGenerator:
    def __init__(self) -> None:
        self.env_builtin = Environment(
            loader=PackageLoader("smal", "codegen.templates"),
            autoescape=select_autoescape([]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def load_builtin_template(self, template_name: str) -> tuple[Template, SMALTemplate]:
        builtin_tmpl = TemplateRegistry.get(template_name)
        return self.env_builtin.get_template(builtin_tmpl.filename), builtin_tmpl

    def load_external_template(self, template_path: str | Path) -> Template:
        template_path = Path(template_path)
        if not template_path.is_file():
            raise FileNotFoundError(f"Template file does not exist: {template_path}")
        env_external = Environment(loader=FileSystemLoader(template_path.parent), autoescape=select_autoescape([]), trim_blocks=True, lstrip_blocks=True)
        return env_external.get_template(template_path.name)

    def render(self, template: Template, smal: SMALFile, **extra_context: Any) -> str:
        # TODO: Implement formatting while the text is in memory here
        return template.render(smal=smal, **extra_context)

    def render_to_file(self, template: Template, smal: SMALFile, out_path: str | Path, force: bool = False, **extra_context: Any) -> None:
        out_path = Path(out_path)
        if not force and out_path.exists():
            raise FileExistsError(f"File already exists and overwrite is not allowed: {out_path}")
        code = self.render(template, smal, **extra_context)
        out_path.write_text(code, encoding="utf-8")
