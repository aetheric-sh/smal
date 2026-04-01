from __future__ import annotations  # Until Python 3.14

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeAlias

from smal.schemas.state_machine import SMALFile

SMALTemplateContextComputeFn: TypeAlias = Callable[[SMALFile], Any]


@dataclass(frozen=True)
class SMALTemplate:
    name: str
    filename: str
    lang: str
    description: str
    output_extension: str
    extra_context: dict[str, Any] = field(default_factory=dict)
    computed_extra_context: dict[str, SMALTemplateContextComputeFn] = field(default_factory=dict)


class TemplateRegistry:
    _templates = {
        "c_machine_hdr": SMALTemplate(
            name="c_machine_hdr",
            filename="c_machine_hdr.j2",
            lang="c",
            description="C header file for the state machine",
            output_extension=".h",
            computed_extra_context={
                "header_guard": lambda smal: f"{smal.name.rstrip('_H')}_H".upper(),
            },
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
