"""Module defining the `validation` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import cmd2
import yaml
from jinja2 import TemplateNotFound, nodes
from pydantic import BaseModel

from smal.codegen.code_generator import SMALCodeGenerator
from smal.repl.helpers import get_parent_app, get_persistence
from smal.schemas.state_machine import SMALFile
from smal.utilities import constants as SMALConstants
from smal.utilities.rules import ALL_RULES

if TYPE_CHECKING:
    import argparse
    from collections.abc import Iterator


_validate_parser = cmd2.Cmd2ArgumentParser()
_validate_parser.add_argument("file", type=Path, completer=cmd2.Cmd.path_complete, help="Path to the SMAL state machine file to validate.")
_validate_parser.add_argument("-e", "--enforce-rules", action="store_true", help="Enforce additional validation rules beyond basic schema validation.")


class ValidateArgs(BaseModel):
    """Model describing the arguments to the validate command."""

    file: Path
    enforce_rules: bool = False


class ValidateCmdSet(cmd2.CommandSet):
    """Command set for handling validation in the SMAL REPL."""

    @cmd2.with_argparser(_validate_parser)
    def do_validate(self, args: argparse.Namespace) -> None:
        """Manage SMAL state machine validation.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = ValidateArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        console = parent_app.get_console()
        if parsed_args.file.suffix in SMALConstants.SupportedFileExtensions.all():
            try:
                file_data = parsed_args.file.read_text()
                model_data = yaml.safe_load(file_data)
                persistence = get_persistence()
                rules_to_reenable: list[str] = []
                if not parsed_args.enforce_rules:
                    rules_to_reenable = [rule.name for rule in ALL_RULES if persistence.is_rule_enabled(rule.name)]
                    console.print(f"Temporarily disabling {len(rules_to_reenable)} rules for validation...")
                    for rule_name in rules_to_reenable:
                        persistence.enable_rule(rule_name, False, write_to_file=False)
                    persistence.save()
                SMALFile.model_validate(model_data)
                parent_app.print_success(f"'{parsed_args.file}' is a valid SMAL file!", prefix="✅")
                if rules_to_reenable:
                    console.print(f"Re-enabling {len(rules_to_reenable)} rules after validation...")
                    for rule_name in rules_to_reenable:
                        persistence.enable_rule(rule_name, True, write_to_file=False)
                    persistence.save()
                return
            except Exception as e:  # noqa: BLE001 - Broad exception caught for user-facing error handling
                parent_app.print_error(f"Invalid SMAL file: {e}", prefix="❌")
                return
        if parsed_args.file.suffix in JinjaTemplateValidator.VALID_EXTENSIONS:
            with console.status("Jinja2 codegen template detected. Validating", spinner="dots"):
                validator = JinjaTemplateValidator(parsed_args.file)
                validation_result = validator.validate()
                validation_result.echo_report(parsed_args.file)
        else:
            parent_app.print_error(
                f"Invalid filetype detected: {parsed_args.file.suffix}. Must be one of {', '.join(JinjaTemplateValidator.VALID_EXTENSIONS)}",
                prefix="❌",
            )


@dataclass(frozen=True)
class TemplateVariableRef:
    """Dataclass representing a reference to a variable in a Jinja2 template, including its name and location."""

    name: str
    line: int
    col: int


@dataclass(frozen=True)
class TemplateMacroRef:
    """Dataclass representing a reference to a macro in a Jinja2 template, including its name, alias, source template, and location."""

    name: str
    alias: str | None
    src_template_ref: str | None
    line: int
    col: int


class Severity(str, Enum):
    """Enumeration of validation issue severity levels, with associated colors for console output."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @cached_property
    def color(self) -> str:
        """Get the rich console color associated with this Severity.

        Returns:
            str: The rich console color associated with this Severity.

        """
        return {
            Severity.ERROR: "red",
            Severity.WARNING: "yellow",
            Severity.INFO: "cyan",
        }[self]


@dataclass
class SMALValidationIssue:
    """Dataclass representing a validation issue found during template validation.

    This includes its severity, message, location, and an optional code for categorization.
    """

    severity: Severity
    message: str
    location: tuple[int, int]
    code: str


@dataclass
class SMALValidationResult:
    """Dataclass representing the result of validating a SMAL template, including the template name and a list of validation issues."""

    template_name: str
    issues: list[SMALValidationIssue] = field(default_factory=list)

    def add_issue(self, severity: Severity, message: str, location: tuple[int, int], code: str) -> None:
        """Add an issue to the result.

        Args:
            severity (Severity): The severity of the issue.
            message (str): The message describing the issue.
            location (tuple[int, int]): The location of the issue in the template (line, column).
            code (str): The code associated with the issue.

        """
        self.issues.append(SMALValidationIssue(severity, message, location, code))

    @property
    def ok(self) -> bool:
        """Get whether or not this validation result has any issues.

        Returns:
            bool: True if there are no issues, False otherwise.

        """
        return all(issue.severity != Severity.ERROR for issue in self.issues)

    def echo_report(self, template_path: Path | None = None) -> None:
        """Echo a report of the validation result to a rich.Console.

        Args:
            template_path (Path | None, optional): The path to the template file. Defaults to None.

        """
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
    """Class for validating Jinja2 templates for use as SMAL code generation templates."""

    VALID_EXTENSIONS: ClassVar[set[str]] = {".j2", ".jinja", ".jinja2", ".tpl", ".template"}

    def __init__(self, template: str | Path) -> None:
        """Initialize the JinjaTemplateValidator.

        Args:
            template (str | Path): The name of a built-in SMAL template or the path to an external Jinja2 template file.

        Raises:
            ValueError: If the provided template is not a recognized built-in template name or a valid file path with a supported extension.
            RuntimeError: If there is an issue loading the template or configuring the Jinja2 environment.
            RuntimeError: If a macro template referenced by a built-in template is found to be invalid during recursive validation.

        """
        self._generator = SMALCodeGenerator()
        if isinstance(template, str):
            self.env = self._generator.env_builtin
            self.template, self.smal_template = self._generator.load_builtin_template(template)
            self.builtin = True
        else:
            if template.suffix.lower() not in self.VALID_EXTENSIONS:
                raise ValueError(
                    f"Template file '{template}' does not have a typical Jinja2 template extension: {template.suffix}. "
                    f"Must be one of {', '.join(self.VALID_EXTENSIONS)}",
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
        """Validate a SMAL file or external template for compliance with SMAL.

        Returns:
            SMALValidationResult: The result of the validation, including any issues found.

        """
        validation_result = SMALValidationResult(self.template_name)
        self._validate_macros(validation_result)
        self._validate_variables(validation_result)
        return validation_result

    @cached_property
    def macro_calls(self) -> set[str]:
        """Get a unique set of macro calls in a jinja2 template.

        Returns:
            set[str]: The set of macro names called in the template.

        """
        macro_calls = set()
        for call in self.ast.find_all(nodes.Call):
            if isinstance(call.node, nodes.Name):
                macro_calls.add(call.node.name)
        return macro_calls

    @cached_property
    def loop_variables(self) -> set[str]:
        """Get a unique set of loop variables in a jinja2 template.

        Returns:
            set[str]: The set of loop variable names used in the template.

        """
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
        """Get an iterator over the macros in a jinja2 template.

        Raises:
            TypeError: If a macro reference cannot be validated due to an unexpected AST node structure.

        Yields:
            Iterator[TemplateMacroRef]: An iterator over the macro references in the template.

        """
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
                    raise TypeError(f"Unable to validate jinja2 macro: {src_template_ref}")

    def variables(self) -> Iterator[TemplateVariableRef]:
        """Get an iterator over the variables in a jinja2 template.

        Yields:
            Iterator[TemplateVariableRef]: The next variable reference in the template, including its name and location.

        """
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
        """Get whether or not the given symbol is a jinja2 template keyword.

        Args:
            symbol (str): The symbol to check.

        Returns:
            bool: True if the symbol is a Jinja2 built-in, False otherwise.

        """
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
            return any(p.startswith((prefix_dot, prefix_arr)) for p in self.allowed_paths)

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
    """Extract all unique member variable paths from a pydantic model schema.

    Args:
        model_schema (dict[str, Any]): The JSON schema of the model to extract paths from.
        prefix (str, optional): The prefix to use for the current path. Defaults to "".
        root_schema (dict[str, Any] | None, optional): The root schema for resolving $ref references. Defaults to None.
        visited_refs (set[str] | None, optional): A set of visited $ref references to avoid infinite recursion. Defaults to None.

    Returns:
        set[str]: A set of unique member variable paths.

    """
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
    """Generate a set of allowed variable paths for a given Pydantic model by analyzing its JSON schema.

    Args:
        model (type[BaseModel]): The Pydantic model class.
        root (str): The root variable name to prefix all paths with. Defaults to "smal".

    Returns:
        set[str]: A set of allowed variable paths.

    """
    model_schema = model.model_json_schema()
    extracted_model_paths = extract_paths_from_model_schema(model_schema)
    return {f"{root}.{path}" for path in extracted_model_paths}
