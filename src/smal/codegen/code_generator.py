from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import Any

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader, Template, select_autoescape

from smal.codegen.templates.builtin_templates import SMALTemplate, TemplateRegistry
from smal.schemas.state_machine import SMALFile


class SMALCodeGenerator:
    def __init__(self) -> None:
        self._internal_loader = PackageLoader("smal", "codegen/templates")

    def _build_env(self, external_template_dir: str | Path | None = None) -> Environment:
        if external_template_dir:
            return Environment(
                loader=ChoiceLoader([self._internal_loader, FileSystemLoader(external_template_dir)]),
                autoescape=select_autoescape([]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        return Environment(
            loader=self._internal_loader,
            autoescape=select_autoescape([]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def load_builtin_template(self, template_name: str) -> tuple[Environment, Template, SMALTemplate]:
        env = self._build_env()
        smal_tmpl = TemplateRegistry.get(template_name)
        tmpl = env.get_template(smal_tmpl.filename)
        return env, tmpl, smal_tmpl

    def load_external_template(self, external_template_filepath: str | Path) -> tuple[Environment, Template]:
        external_template_filepath = Path(external_template_filepath)
        if not external_template_filepath.is_file():
            raise FileNotFoundError(f"Template file does not exist: {external_template_filepath}")
        env = self._build_env(external_template_dir=external_template_filepath.parent)
        tmpl = env.get_template(external_template_filepath.name)
        return env, tmpl

    def render(self, template: Template, smal: SMALFile, **extra_context: Any) -> str:
        # TODO: Implement formatting while the text is in memory here
        return template.render(smal=smal, **extra_context)

    def render_to_file(self, template: Template, smal: SMALFile, out_path: str | Path, force: bool = False, **extra_context: Any) -> None:
        out_path = Path(out_path)
        if not force and out_path.exists():
            raise FileExistsError(f"File already exists and overwrite is not allowed: {out_path}")
        code = self.render(template, smal, **extra_context)
        out_path.write_text(code, encoding="utf-8")
