"""Module defining the code generator for the SMAL CLI program."""

from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import Any

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader, StrictUndefined, Template, UndefinedError, select_autoescape

from smal.codegen.naming import available_naming_layers
from smal.codegen.templates.builtin_templates import SMALTemplate, TemplateRegistry
from smal.schemas.machine import Machine  # noqa: TC001


class SMALCodeGenerator:
    """Code generator that takes in a SMAL file and generates jinja templated code."""

    def __init__(self) -> None:
        """Initialize the SMALCodeGenerator."""
        self._internal_loader = PackageLoader("smal", "codegen")

    def _build_env(self, external_template_dir: str | Path | None = None) -> Environment:
        loader = ChoiceLoader([self._internal_loader, FileSystemLoader(external_template_dir)]) if external_template_dir else self._internal_loader
        env = Environment(
            loader=loader,
            autoescape=select_autoescape([]),
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )
        # Each language's naming conventions are available to every template as `<lang>_<name>` filters, e.g. `c_type_name`
        for lang, layer in available_naming_layers().items():
            env.filters.update(
                {
                    f"{lang}_type_name": layer.type_name,
                    f"{lang}_field_decl": layer.field_decl,
                    f"{lang}_enum_member": layer.enum_member,
                    f"{lang}_enum_name": layer.enum_name,
                    f"{lang}_enum_count": layer.enum_count,
                    f"{lang}_enum_null": layer.enum_null,
                },
            )
        return env

    def load_builtin_template(self, template_name: str) -> tuple[Environment, Template, SMALTemplate]:
        """Load a SMAL-provided built in jinja template.

        Args:
            template_name (str): The name of the builtin template to load.

        Returns:
            tuple[Environment, Template, SMALTemplate]: The jinja environment, jinja template and SMALTemplate objects.

        """
        env = self._build_env()
        smal_tmpl = TemplateRegistry.get(template_name)
        # Jinja2 template names always use forward slashes, regardless of OS.
        filepath = f"templates/{smal_tmpl.lang}/{smal_tmpl.filename}"
        tmpl = env.get_template(filepath)
        return env, tmpl, smal_tmpl

    def load_external_template(self, external_template_filepath: str | Path) -> tuple[Environment, Template]:
        """Load a jinja template that is externally provided by the user.

        Args:
            external_template_filepath (str | Path): The filepath to the user-provided template.

        Raises:
            FileNotFoundError: If the file could not be found.

        Returns:
            tuple[Environment, Template]: The jinja environment and template.

        """
        external_template_filepath = Path(external_template_filepath)
        if not external_template_filepath.is_file():
            raise FileNotFoundError(f"Template file does not exist: {external_template_filepath}")
        env = self._build_env(external_template_dir=external_template_filepath.parent)
        tmpl = env.get_template(external_template_filepath.name)
        return env, tmpl

    def render(self, template: Template, machine: Machine, **extra_context: Any) -> str:
        """Render the given template using the given SMAL file, and any provided extra content.

        Args:
            template (Template): The jinja template to render.
            machine (Machine): The SMAL state machine to render to the template.
            **extra_context (Any): Any extra content provided as kwargs to render in the template.

        Raises:
            ValueError: If the template cannot be rendered due to missing variables in the context.

        Returns:
            str: The rendered template, ready to be written to a file.

        """
        # TODO: Implement formatting while the text is in memory here
        try:
            return template.render(machine=machine, **extra_context)
        except UndefinedError as e:
            raise ValueError(
                f"Unable to render template due to the following undefined variable error:\n\n{e}\n\n"
                "Consider adding definitions of these variables in the metadata of your SMAL file.",
            ) from e

    def render_to_file(self, template: Template, machine: Machine, out_path: str | Path, force: bool = False, **extra_context: Any) -> None:
        """Render the given template using the given SMAL file, and any provided extra content to the given filepath.

        Args:
            template (Template): The jinja template to render.
            machine (Machine): The SMAL state machine to render to the template.
            out_path (str | Path): The output filepath to write the file content to.
            force (bool, optional): Whether or not to forcefully overwrite an existing file. Defaults to False.
            **extra_context (Any): Any extra content provided as kwargs to render in the template.

        Raises:
            FileExistsError: If the file already exists and force is false.
            ValueError: If the template cannot be rendered due to missing variables in the context.

        """
        out_path = Path(out_path)
        if not force and out_path.exists():
            raise FileExistsError(f"File already exists and overwrite is not allowed: {out_path}")
        try:
            code = self.render(template, machine, **extra_context)
        except ValueError:  # noqa: TRY203 - Error will automatically re-raise. Keeping for clarity
            raise
        out_path.write_text(code, encoding="utf-8")
