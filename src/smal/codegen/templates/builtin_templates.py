"""Module defining built-in templates for SMAL code generation."""

from __future__ import annotations  # Until Python 3.14

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeAlias

from smal.schemas.debug import DebugCodegenContext
from smal.schemas.machine import Machine

SMALTemplateContextComputeFn: TypeAlias = Callable[[Machine], Any]


@dataclass(frozen=True)
class SMALTemplate:
    """Model describing a SMAL code generation template."""

    name: str
    filename: str
    lang: str
    description: str
    output_extension: str
    extra_context: dict[str, Any] = field(default_factory=dict)
    computed_extra_context: dict[str, SMALTemplateContextComputeFn] = field(default_factory=dict)


class TemplateRegistry:
    """Namespace class for managing SMAL code generation templates."""

    # To prevent a mutable default class variable, we initialize the templates dictionary lazily in the _get_templates method
    _templates: dict[str, SMALTemplate] | None = None

    @classmethod
    def _get_templates(cls) -> dict[str, SMALTemplate]:
        """Get the dictionary of templates, initializing it if it has not already been initialized."""
        if cls._templates is None:
            cls._templates = {
                "c_dbg_boilerplate_hdr": SMALTemplate(
                    name="c_dbg_boilerplate_hdr",
                    filename="c_dbg_boilerplate_hdr.j2",
                    lang="c",
                    description="C header file for the state machine debug boilerplate code",
                    output_extension=".h",
                    computed_extra_context={"dbg_ctx": DebugCodegenContext.build},
                ),
                "c_dbg_boilerplate_src": SMALTemplate(
                    name="c_dbg_boilerplate_src",
                    filename="c_dbg_boilerplate_src.j2",
                    lang="c",
                    description="C source file for the state machine debug boilerplate code",
                    output_extension=".c",
                    computed_extra_context={"dbg_ctx": DebugCodegenContext.build},
                ),
                "c_machine_hdr": SMALTemplate(
                    name="c_machine_hdr",
                    filename="c_machine_hdr.j2",
                    lang="c",
                    description="C header file for the state machine",
                    output_extension=".h",
                    computed_extra_context={
                        "header_guard": lambda smal: f"{smal.name.strip().rstrip('_H')}_H".upper(),
                    },
                ),
            }
        return cls._templates

    def __new__(cls) -> None:
        """Create a new instance of the TemplateRegistry.

        Raises:
            NotImplementedError: TemplateRegistry is a namespace class and cannot be instantiated.

        """
        raise NotImplementedError("TemplateRegistry is a namespace class and cannot be instantiated.")

    @classmethod
    def get(cls, name: str) -> SMALTemplate:
        """Get a SMAL template by name.

        Args:
            name (str): The name of the template to retrieve.

        Raises:
            ValueError: If the template with the given name does not exist.

        Returns:
            SMALTemplate: The SMAL template with the given name.

        """
        templates = cls._get_templates()
        if name not in templates:
            raise ValueError(f"Unknown template: {name}")
        return templates[name]

    @classmethod
    def get_dbg_boilerplate_templates(cls, lang: str) -> list[SMALTemplate]:
        """Get the debug boilerplate code templates for the given language.

        Args:
            lang (str): The language to get the debug boilerplate code templates for.

        Returns:
            list[SMALTemplate]: The list of debug boilerplate code templates for the given language.

        """
        return {
            "c": [cls.get("c_dbg_boilerplate_hdr"), cls.get("c_dbg_boilerplate_src")],
        }.get(lang, [])

    @classmethod
    def list_templates(cls) -> list[SMALTemplate]:
        """List all builtin SMAL templates.

        Returns:
            list[SMALTemplate]: The list of all builtin SMAL templates.

        """
        templates = cls._get_templates()
        return list(templates.values())

    @classmethod
    def list_template_names(cls) -> list[str]:
        """List all builtin SMAL template names.

        Returns:
            list[str]: The list of all builtin SMAL template names.

        """
        templates = cls._get_templates()
        return list(templates.keys())

    @classmethod
    def has_template(cls, name: str) -> bool:
        """Get whether or not a template with the given name exists.

        Args:
            name (str): The name of the template to check for.

        Returns:
            bool: True if the template with the given name exists, False otherwise.

        """
        templates = cls._get_templates()
        return name in templates
