from __future__ import annotations
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from smal.schemas.smal_file import SMALFile
from typing import Any

class SMALCodeGenerator:

    def __init__(self, template_dir: str | Path) -> None:
        template_dir = Path(template_dir)
        if not template_dir.exists():
            raise ValueError(f"Codegen template directory does not exist: {template_dir}")
        self.env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape([]), trim_blocks=True, lstrip_blocks=True)
    
    def render(self, template_name: str, smal: SMALFile, **extra_content: Any) -> str:
        template = self.env.get_template(template_name)
        context = {
            "smal": smal,
            "machine": smal.machine,
            "states": smal.states,
            "events": smal.events,
            "commands": smal.commands,
            "errors": smal.errors,
            "transitions": smal.transitions,
            "debug": smal.debug,
        }
        context.update(extra_content)
        return template.render(**context)
    
    def render_to_file(self, template_name: str, smal: SMALFile, out_path: str | Path, **extra_content: Any) -> None:
        out_path = Path(out_path)
        code = self.render(template_name, smal, **extra_content)
        out_path.write_text(code, encoding="utf-8")
