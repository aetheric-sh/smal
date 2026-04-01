from __future__ import annotations  # Until Python 3.14

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar

import typer
from jinja2 import TemplateNotFound, nodes
from pydantic import BaseModel
from rich.console import Console

from smal.codegen.code_generator import SMALCodeGenerator
from smal.schemas import SMALFile
from smal.utilities import constants as SMALConstants

validate_app = typer.Typer(help="Validate .smal files and external Jinja2 templates for compliance/compatibility with SMAL.")


@validate_app.callback(invoke_without_command=True)
def validate_root(
    filepath: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to the .smal or .j2 file to validate."),
) -> None:
    console = Console()
    if filepath.suffix in SMALConstants.SupportedFileExtensions.all():
        with console.status(" SMAL file detected. Validating", spinner="dots"):
            pass
    elif filepath.suffix in JinjaTemplateValidator.VALID_EXTENSIONS:
        with console.status(" Jinja2 codegen template detected. Validating", spinner="dots"):
            validator = JinjaTemplateValidator(filepath)
            validation_result = validator.validate()
            validation_result.echo_report(filepath)
    else:
        typer.BadParameter(f"Invalid filetype detected: {filepath.suffix}")


@dataclass(frozen=True)
class TemplateVariableRef:
    name: str
    line: int
    col: int


@dataclass(frozen=True)
class TemplateMacroRef:
    name: str
    alias: str | None
    src_template_ref: str | None
    line: int
    col: int


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @cached_property
    def color(self) -> str:
        return {
            Severity.ERROR: "red",
            Severity.WARNING: "yellow",
            Severity.INFO: "cyan",
        }[self]


@dataclass
class SMALValidationIssue:
    severity: Severity
    message: str
    location: tuple[int, int]
    code: str


@dataclass
class SMALValidationResult:
    template_name: str
    issues: list[SMALValidationIssue] = field(default_factory=list)

    def add_issue(self, severity: Severity, message: str, location: tuple[int, int], code: str) -> None:
        self.issues.append(SMALValidationIssue(severity, message, location, code))

    @property
    def ok(self) -> bool:
        return all(issue.severity != Severity.ERROR for issue in self.issues)

    def echo_report(self, template_path: Path | None = None) -> None:
        from rich.console import Console
        from rich.padding import Padding
        from rich.text import Text

        console = Console()
        console.print(f"[bold underline cyan]Validation Report for: {self.template_name}[/bold underline cyan]")
        if template_path:
            console.print(f"Location: {template_path}")
        if not self.issues:
            console.print(f"[green]No issues found! [bold cyan]'{self.template_name}'[/bold cyan] is a valid SMAL code generation template![/green]")
            return
        for issue in self.issues:
            header = Text()
            header.append(issue.severity.name, style=issue.severity.color)
            header.append(f" {issue.code}", style="yellow")
            header.append(f" at {f'{template_path}::' if template_path else ''}{issue.location[0]}:{issue.location[1]}")
            console.print(header)
            console.print(Padding(issue.message, pad=(0, 0, 0, 4)))


class JinjaTemplateValidator:
    VALID_EXTENSIONS: ClassVar[set[str]] = {".j2", ".jinja", ".jinja2", ".tpl", ".template"}

    def __init__(self, template: str | Path) -> None:
        self._generator = SMALCodeGenerator()
        if isinstance(template, str):
            self.env = self._generator.env_builtin
            self.template, self.smal_template = self._generator.load_builtin_template(template)
            self.builtin = True
        else:
            if template.suffix.lower() not in self.VALID_EXTENSIONS:
                raise ValueError(
                    f"Template file '{template}' does not have a typical Jinja2 template extension: {template.suffix}. Must be one of {', '.join(self.VALID_EXTENSIONS)}",
                )
            self.env, self.template = self._generator.load_external_template(template)
            self.builtin = False
        if self.env.loader is None:
            raise RuntimeError("Jinja2 environment loader is not configured.")
        if self.template.name is None:
            raise RuntimeError("Unable to determine Jinja2 template name.")
        self.template_name = self.template.name
        self.template_source, _, _ = self.env.loader.get_source(self.env, self.template.name)
        self.template_lines = self.template_source.splitlines()
        self.allowed_paths = generate_allowed_variable_paths_from_model(SMALFile)
        self.ast = self.env.parse(self.template_source)

    def validate(self) -> SMALValidationResult:
        validation_result = SMALValidationResult(self.template_name)
        self._validate_macros(validation_result)
        self._validate_variables(validation_result)
        return validation_result

    @cached_property
    def macro_calls(self) -> set[str]:
        macro_calls = set()
        for call in self.ast.find_all(nodes.Call):
            if isinstance(call.node, nodes.Name):
                macro_calls.add(call.node.name)
        return macro_calls

    @cached_property
    def loop_variables(self) -> set[str]:
        loop_vars = set()
        for loop in self.ast.find_all(nodes.For):
            target = loop.target
            if isinstance(target, nodes.Name):
                loop_vars.add(target.name)
            elif isinstance(target, nodes.Tuple):
                for elem in target.items:
                    if isinstance(elem, nodes.Name):
                        loop_vars.add(elem.name)
        return loop_vars

    def macros(self) -> Iterator[TemplateMacroRef]:
        for node in self.ast.find_all(nodes.FromImport):
            src_template_ref = node.template.value if isinstance(node.template, nodes.Const) else None
            if not src_template_ref:
                continue
            col = self._extract_template_column(self.template_lines, node.lineno, "import")
            for name in node.names:
                if isinstance(name, str):
                    yield TemplateMacroRef(name, None, src_template_ref, node.lineno, col)
                elif isinstance(name, tuple):
                    yield TemplateMacroRef(name[0], name[1], src_template_ref, node.lineno, col)
                else:
                    raise RuntimeError(f"Unable to validate jinja2 macro: {src_template_ref}")

    def variables(self) -> Iterator[TemplateVariableRef]:
        for node in self.ast.find_all(nodes.Name):
            if node.name in self.macro_calls:
                continue  # Ignore calls to macros, we validate those elsewhere
            if node.ctx != "load":
                continue  # ctx==load means we are reading an existing var
            if node.name in self.loop_variables:
                continue  # Ignore variables created as part of jinja loops
            variable_name = node.name
            variable_lineno = node.lineno
            variable_colno = self._extract_template_column(self.template_lines, variable_lineno, variable_name)
            yield TemplateVariableRef(variable_name, variable_lineno, variable_colno)

    @staticmethod
    def is_jinja2_builtin(symbol: str) -> bool:
        # This is a simplified check. In reality, Jinja2 has many built-in variables and functions.
        jinja2_builtins = {"loop", "self", "super", "config", "namespace"}
        return symbol in jinja2_builtins

    @staticmethod
    def _extract_template_column(lines: list[str], lineno: int, variable_name: str) -> int:
        if 1 <= lineno <= len(lines):
            text_line = lines[lineno - 1]
            colno = text_line.find(variable_name)
            return colno if colno != -1 else 0
        return 0

    def _validate_macros(self, result: SMALValidationResult) -> None:
        for ref in self.macros():
            if not ref.src_template_ref:
                continue
            try:
                self.env.get_template(ref.src_template_ref)
                # If we're working with a SMAL-provided template, we want to recursively validate all referenced macro templates
                # This is to ensure all templates SMAL provides are adherent
                if self.builtin:
                    recursive_validator = JinjaTemplateValidator(ref.name)
                    recursive_result = recursive_validator.validate()
                    if not recursive_result.ok:
                        recursive_result.echo_report()
                        raise RuntimeError("Macro source template is invalid.")
            except TemplateNotFound:
                result.add_issue(
                    Severity.ERROR,
                    f"Macro template '{ref.src_template_ref}' not found.",
                    (ref.line, ref.col),
                    code="MACRO_TEMPLATE_NOT_FOUND",
                )

    def _validate_variables(self, result: SMALValidationResult) -> None:
        def is_allowed_symbol(symbol: str) -> bool:
            if symbol in self.allowed_paths:
                return True
            if symbol.startswith("smal.metadata"):
                return True  # Allow arbitrary metadata from the SMAL file
            prefix_dot = symbol + "."
            prefix_arr = symbol + "[]"
            for p in self.allowed_paths:
                if p.startswith(prefix_dot) or p.startswith(prefix_arr):
                    return True
            return False

        for ref in self.variables():
            if self.is_jinja2_builtin(ref.name):
                continue
            if not is_allowed_symbol(ref.name):
                result.add_issue(
                    Severity.ERROR,
                    f"Unknown variable '{ref.name}' used in template '{self.template_name}'",
                    location=(ref.line, ref.col),
                    code="UNDEFINED_VARIABLE",
                )


def extract_paths_from_model_schema(
    model_schema: dict[str, Any],
    prefix: str = "",
    root_schema: dict[str, Any] | None = None,
    visited_refs: set[str] | None = None,
) -> set[str]:
    if root_schema is None:
        root_schema = model_schema
    if visited_refs is None:
        visited_refs = set()

    paths = set()

    # --- $ref resolution with cycle detection ---
    if "$ref" in model_schema:
        ref: str = model_schema["$ref"]

        # If we've already expanded this ref, stop recursion
        if ref in visited_refs:
            if prefix:
                paths.add(prefix)
            return paths

        visited_refs.add(ref)

        if ref.startswith("#/$defs/"):
            type_name = ref.rsplit("/", maxsplit=1)[-1]
            defs = root_schema.get("$defs") or root_schema.get("definitions") or {}
            subschema = defs.get(type_name)
            if subschema is None:
                if prefix:
                    paths.add(prefix)
                return paths
            return extract_paths_from_model_schema(subschema, prefix, root_schema, visited_refs)
        if prefix:
            paths.add(prefix)
        return paths

    schema_type = model_schema.get("type")

    # --- Objects ---
    if schema_type == "object":
        props = model_schema.get("properties", {})
        for name, subschema in props.items():
            new_prefix = f"{prefix}.{name}" if prefix else name
            paths |= extract_paths_from_model_schema(subschema, new_prefix, root_schema, visited_refs)
        return paths

    # --- Arrays ---
    if schema_type == "array":
        items = model_schema.get("items", {})
        new_prefix = f"{prefix}[]" if prefix else "[]"
        return extract_paths_from_model_schema(items, new_prefix, root_schema, visited_refs)

    # --- anyOf / oneOf ---
    if "anyOf" in model_schema:
        for option in model_schema["anyOf"]:
            paths |= extract_paths_from_model_schema(option, prefix, root_schema, visited_refs)
        return paths

    if "oneOf" in model_schema:
        for option in model_schema["oneOf"]:
            paths |= extract_paths_from_model_schema(option, prefix, root_schema, visited_refs)
        return paths

    # --- Primitives ---
    if schema_type in {"string", "number", "integer", "boolean", "null"}:
        if prefix:
            paths.add(prefix)
        return paths

    # --- Fallback ---
    if prefix:
        paths.add(prefix)
    return paths


def generate_allowed_variable_paths_from_model(model: type[BaseModel], root: str = "smal") -> set[str]:
    """Generates a set of allowed variable paths for a given Pydantic model by analyzing its JSON schema.

    Args:
        model (type[BaseModel]): The Pydantic model class.

    Returns:
        set[str]: A set of allowed variable paths.

    """
    model_schema = model.model_json_schema()
    extracted_model_paths = extract_paths_from_model_schema(model_schema)
    return {f"{root}.{path}" for path in extracted_model_paths}
