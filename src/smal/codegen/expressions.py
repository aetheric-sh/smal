"""Bind SMAL expressions to machine definitions before target language emission."""

from __future__ import annotations

import ast
import math
import operator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from smal.schemas.enumeration import Enumeration
from smal.utilities import expressions
from smal.utilities.types import SMALPrimitive

if TYPE_CHECKING:
    from smal.schemas.action import Action
    from smal.schemas.guard import GuardDef
    from smal.schemas.machine import Machine

ExpressionType = SMALPrimitive | Enumeration
_ARITHMETIC = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul}


@dataclass(frozen=True)
class BoundLiteral:
    """A literal boolean or number."""

    value: bool | int | float
    datatype: SMALPrimitive


@dataclass(frozen=True)
class BoundReference:
    """A reference resolved to a context field, constant, or member of a specific enum."""

    name: str
    kind: Literal["context", "constant", "enum_member"]
    datatype: ExpressionType
    constant_value: int | None = None


@dataclass(frozen=True)
class BoundOperation:
    """An operation with typed operands in evaluation order."""

    operator: type[ast.boolop | ast.unaryop | ast.cmpop | ast.operator]
    operands: tuple[BoundExpression, ...]
    datatype: ExpressionType
    integer_range: tuple[int, int] | None = None


BoundExpression = BoundLiteral | BoundReference | BoundOperation


@dataclass(frozen=True)
class BoundAssignment:
    """An assignment to a typed context field."""

    field_name: str
    datatype: ExpressionType
    expression: BoundExpression


def bind_setter(machine: Machine, action: Action, field_name: str, value: bool | float | str) -> BoundAssignment:
    """Resolve and type-check one setter against its destination field."""
    try:
        return _Binder(machine, allow_arithmetic=True).assignment(field_name, value)
    except ValueError as exc:
        raise ValueError(f"Machine '{machine.name}', action '{action.name}', assignment to '{field_name}' with {value!r}: {exc}") from exc


def bind_guard(machine: Machine, guard: GuardDef) -> BoundExpression | None:
    """Bind a declarative guard, or return None for a handwritten guard."""
    if guard.expr is None:
        return None
    try:
        tree = expressions.parse(guard.expr)
        result = _Binder(machine).bind(tree)
        _require_bool(result)
    except ValueError as exc:
        raise ValueError(f"Machine '{machine.name}', guard '{guard.name}', expression {guard.expr!r}: {exc}") from exc
    return result


class _Binder:
    def __init__(self, machine: Machine, *, allow_arithmetic: bool = False) -> None:
        self.context = {field.name: field.type for field in machine.context}
        self.constants = {constant.name: constant.value for constant in machine.constants}
        self.machine = machine
        self.allow_arithmetic = allow_arithmetic

    def assignment(self, field_name: str, value: bool | float | str) -> BoundAssignment:
        if field_name not in self.context:
            raise ValueError(f"Unknown context field '{field_name}'.")
        datatype = self.machine.resolve_context_type(self.context[field_name])
        expected_enum = datatype if isinstance(datatype, Enumeration) else None
        if isinstance(value, str):
            expression = self.bind(expressions.parse(value), expected_enum)
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("Floating-point literals must be finite.")
            expression = BoundLiteral(value, SMALPrimitive.FLOAT64)
        else:
            expression = self.bind(ast.Constant(value=value))
        source_type = expression.datatype
        if source_type != datatype and not (
            isinstance(datatype, SMALPrimitive)
            and isinstance(source_type, SMALPrimitive)
            and ((datatype.is_integer and source_type.is_integer) or (datatype.is_float and _is_numeric(source_type)))
        ):
            raise ValueError("Expression type is incompatible with the destination field.")
        if isinstance(datatype, SMALPrimitive) and isinstance(expression, BoundLiteral):
            datatype.check_value(expression.value)
        return BoundAssignment(field_name, datatype, expression)

    def bind(self, node: ast.expr, expected_enum: Enumeration | None = None) -> BoundExpression:
        if isinstance(node, ast.Name):
            return self._reference(node.id, expected_enum)
        if isinstance(node, ast.Constant):
            datatype = SMALPrimitive.BOOL if isinstance(node.value, bool) else _integer_type(node.value)
            return BoundLiteral(node.value, datatype)
        if isinstance(node, ast.BoolOp):
            operands = tuple(self.bind(child) for child in node.values)
            for operand in operands:
                _require_bool(operand)
            return BoundOperation(type(node.op), operands, SMALPrimitive.BOOL)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            operand = self.bind(node.operand)
            _require_bool(operand)
            return BoundOperation(ast.Not, (operand,), SMALPrimitive.BOOL)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant) and type(node.operand.value) is int:
            value = -node.operand.value
            return BoundLiteral(value, _integer_type(value))
        if isinstance(node, ast.Compare):
            return self._comparison(node)
        if self.allow_arithmetic and isinstance(node, ast.BinOp) and type(node.op) in _ARITHMETIC:
            return self._arithmetic(node)
        raise ValueError(f"Unsupported syntax for code generation: {ast.unparse(node)!r}.")

    def _reference(self, name: str, expected_enum: Enumeration | None) -> BoundReference:
        if name in self.context:
            return BoundReference(name, "context", self.machine.resolve_context_type(self.context[name]))
        if name in self.constants:
            value = self.constants[name]
            if not isinstance(value, int):
                raise ValueError(f"Constant '{name}' must be numeric in a generated expression.")
            return BoundReference(name, "constant", _integer_type(value), constant_value=value)
        if expected_enum is not None:
            if name not in expected_enum.resolved_values:
                raise ValueError(f"'{name}' is not a member of enum '{expected_enum.name}'.")
            return BoundReference(name, "enum_member", expected_enum)
        matches = [enum for enum in self.machine.enums if name in enum.resolved_values]
        if len(matches) == 1:
            return BoundReference(name, "enum_member", matches[0])
        if matches:
            raise ValueError(f"Ambiguous enum member '{name}' in {', '.join(enum.name for enum in matches)}.")
        raise ValueError(f"Unknown name '{name}'.")

    def _context_enum(self, node: ast.expr) -> Enumeration | None:
        if isinstance(node, ast.Name) and node.id in self.context:
            datatype = self.machine.resolve_context_type(self.context[node.id])
            if isinstance(datatype, Enumeration):
                return datatype
        return None

    def _comparison(self, node: ast.Compare) -> BoundOperation:
        if len(node.ops) != 1:
            raise ValueError("Chained comparisons are unsupported for code generation.")
        right_node = node.comparators[0]
        left = self.bind(node.left, self._context_enum(right_node))
        right = self.bind(right_node, self._context_enum(node.left))
        op = type(node.ops[0])
        left_type, right_type = left.datatype, right.datatype
        if _is_numeric(left_type) and _is_numeric(right_type):
            return BoundOperation(op, (left, right), SMALPrimitive.BOOL)
        if op in (ast.Eq, ast.NotEq) and left_type == right_type:
            return BoundOperation(op, (left, right), SMALPrimitive.BOOL)
        raise ValueError(f"Incompatible operands for comparison {ast.unparse(node)!r}.")

    def _arithmetic(self, node: ast.BinOp) -> BoundOperation:
        left, right = self.bind(node.left), self.bind(node.right)
        left_range, right_range = integer_range(left), integer_range(right)
        if left_range is None or right_range is None:
            raise ValueError("Generated arithmetic requires integer operands.")
        op = type(node.op)
        calculate = _ARITHMETIC[op]
        results = [calculate(x, y) for x in left_range for y in right_range]
        bounds = [*left_range, *right_range, *results]
        if min(bounds) < SMALPrimitive.INT64.min_value or max(bounds) > SMALPrimitive.INT64.max_value:
            raise ValueError("Arithmetic operands or intermediate results may exceed the supported signed 64-bit range.")
        return BoundOperation(op, (left, right), SMALPrimitive.INT64, (min(results), max(results)))


def integer_range(expression: BoundExpression) -> tuple[int, int] | None:
    """Return the known lower and upper bounds of a bound integer expression."""
    datatype = expression.datatype
    if not isinstance(datatype, SMALPrimitive) or not datatype.is_integer:
        return None
    if isinstance(expression, BoundLiteral):
        value = int(expression.value)
        return value, value
    if isinstance(expression, BoundReference) and expression.constant_value is not None:
        return expression.constant_value, expression.constant_value
    if isinstance(expression, BoundOperation) and expression.integer_range is not None:
        return expression.integer_range
    assert datatype.min_value is not None
    assert datatype.max_value is not None
    return datatype.min_value, datatype.max_value


def _is_numeric(datatype: ExpressionType) -> bool:
    return isinstance(datatype, SMALPrimitive) and (datatype.is_integer or datatype.is_float)


def _integer_type(value: int) -> SMALPrimitive:
    datatype = SMALPrimitive.INT64 if value <= SMALPrimitive.INT64.max_value else SMALPrimitive.UINT64
    datatype.check_value(value)
    return datatype


def _require_bool(expression: BoundExpression) -> None:
    if expression.datatype != SMALPrimitive.BOOL:
        raise ValueError("Guard conditions and boolean operators require boolean operands.")
