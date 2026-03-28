from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeAlias

from jinja2 import Environment, FileSystemLoader, meta, select_autoescape
from pydantic import BaseModel

from smal.schemas.smal_file import SMALFile


def enumerate_schema_paths(schema: dict[str, Any], prefix: str = "") -> set[str]:
    paths = set()
    schema_type = schema.get("type")
    match schema_type:
        case "object":
            props = schema.get("properties", {})
            for prop_name, prop_schema in props.items():
                new_prefix = f"{prefix}.{prop_name}" if prefix else prop_name
                paths.add(new_prefix)
                paths |= enumerate_schema_paths(prop_schema, prefix=new_prefix)
        case "array":
            item_schema = schema.get("items", {})
            new_prefix = f"{prefix}[]" if prefix else "[]"
            paths.add(new_prefix)
            paths |= enumerate_schema_paths(item_schema, prefix=new_prefix)
        case _:
            pass
    return paths


def allowed_template_paths_for_model(model_cls: type[BaseModel]) -> set[str]:
    schema = model_cls.model_json_schema()
    raw_paths = enumerate_schema_paths(schema)
    return {f"smal.{p}" for p in raw_paths}


def is_valid_smal_template(template_path: str | Path) -> tuple[bool, set[str]]:
    template_path = Path(template_path)
    if not template_path.is_file():
        raise FileNotFoundError(f"Template file does not exist: {template_path}")
    env = Environment(loader=FileSystemLoader(Path(template_path).parent), autoescape=select_autoescape([]), trim_blocks=True, lstrip_blocks=True)
    if env.loader is None:
        raise RuntimeError(f"Failed to create Jinja2 environment with loader for template: {template_path}")
    source = env.loader.get_source(env, template_path.name)[0]
    ast = env.parse(source)
    referenced_vars = meta.find_undeclared_variables(ast)
    allowed_vars = allowed_template_paths_for_model(SMALFile)
    is_valid = referenced_vars.issubset(allowed_vars)
    return is_valid, referenced_vars - allowed_vars


SMALTemplateContextComputeFn: TypeAlias = Callable[[SMALFile], Any]


@dataclass(frozen=True)
class SMALTemplate:
    name: str
    filename: str
    description: str
    output_extension: str
    extra_context: dict[str, Any] = field(default_factory=dict)
    computed_extra_context: dict[str, SMALTemplateContextComputeFn] = field(default_factory=dict)


class TemplateRegistry:
    _templates = {
        "c-machine-hdr": SMALTemplate(
            name="c-machine-hdr",
            filename="c_machine_hdr.j2",
            description="C header file for the state machine",
            output_extension=".h",
            computed_extra_context={
                "header_guard": lambda smal: f"{smal.machine.rstrip('_H')}_H".upper(),
            },
        ),
        "c-machine-src": SMALTemplate(
            name="c-machine-src",
            filename="c_machine_src.j2",
            description="C source file for the state machine",
            output_extension=".c",
        ),
    }

    def __new__(cls) -> None:
        raise NotImplementedError("TemplateRegistry is a namespace class and cannot be instantiated.")

    @classmethod
    def get(cls, name: str) -> SMALTemplate:
        if name not in cls._templates:
            raise ValueError(f"Unknown template: {name}")
        return cls._templates[name]

    @classmethod
    def list_templates(cls) -> list[SMALTemplate]:
        return list(cls._templates.values())

    @classmethod
    def list_template_names(cls) -> list[str]:
        return list(cls._templates.keys())

    @classmethod
    def has_template(cls, name: str) -> bool:
        return name in cls._templates
