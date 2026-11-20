"""Emit C expressions and assignments from bound SMAL expressions."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from smal.codegen.expressions import BoundLiteral, BoundReference, integer_range
from smal.schemas.enumeration import Enumeration
from smal.utilities.types import SMALPrimitive

if TYPE_CHECKING:
    from collections.abc import Callable

    from smal.codegen.expressions import BoundAssignment, BoundExpression

_COMPARISONS = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}
_ARITHMETIC = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*"}
_OPPOSITE_SIGN_RESULTS = {
    ast.Eq: ("false", "false"),
    ast.NotEq: ("true", "true"),
    ast.Lt: ("true", "false"),
    ast.LtE: ("true", "false"),
    ast.Gt: ("false", "true"),
    ast.GtE: ("false", "true"),
}


def integer_literal(value: int) -> str:
    """Spell integers at the 64-bit boundaries without relying on compiler extensions."""
    if value == SMALPrimitive.INT64.min_value:
        return "INT64_MIN"
    if SMALPrimitive.INT64.max_value < value <= SMALPrimitive.UINT64.max_value:
        return f"UINT64_C({value})"
    return str(value)


def emit_guard_expression(expression: BoundExpression, enum_member: Callable[[str, str], str]) -> str:
    """Render a bound guard using the built-in C machine's context and symbol conventions."""
    return _emit_expression(expression, enum_member)


def _emit_expression(expression: BoundExpression, enum_member: Callable[[str, str], str]) -> str:
    if isinstance(expression, BoundLiteral):
        if isinstance(expression.value, bool):
            return "true" if expression.value else "false"
        if isinstance(expression.value, float):
            return repr(expression.value)
        return integer_literal(expression.value)
    if isinstance(expression, BoundReference):
        if expression.kind == "context":
            return f"state_machine->context.{expression.name}"
        if expression.kind == "constant":
            return expression.name.upper()
        if isinstance(expression.datatype, Enumeration):
            return enum_member(expression.name, expression.datatype.name)
        raise ValueError(f"Enum member '{expression.name}' lacks a resolved enum type.")

    operands = tuple(_emit_expression(operand, enum_member) for operand in expression.operands)
    op = expression.operator
    if op is ast.Not:
        return f"(!{operands[0]})"
    if op in (ast.And, ast.Or):
        separator = " && " if op is ast.And else " || "
        return f"({separator.join(operands)})"
    if op in _ARITHMETIC:
        left, right = operands
        return f"((int64_t)({left}) {_ARITHMETIC[op]} (int64_t)({right}))"
    if op not in _COMPARISONS:
        raise ValueError(f"Unsupported C guard operator: {op.__name__}.")
    left, right = operands
    left_type, right_type = (operand.datatype for operand in expression.operands)
    operator = _COMPARISONS[op]
    if isinstance(left_type, SMALPrimitive) and isinstance(right_type, SMALPrimitive):
        if left_type.is_integer and right_type.is_integer:
            if SMALPrimitive.UINT64 not in (left_type, right_type):
                return f"((int64_t)({left}) {operator} (int64_t)({right}))"
            comparison = f"((uint64_t)({left}) {operator} (uint64_t)({right}))"
            negative_left, negative_right = _OPPOSITE_SIGN_RESULTS[op]
            if left_type.min_value < 0:
                return f"(({left}) < 0 ? {negative_left} : {comparison})"
            if right_type.min_value < 0:
                return f"(({right}) < 0 ? {negative_right} : {comparison})"
            return comparison
        if (left_type.is_float and right_type.is_integer) or (right_type.is_float and left_type.is_integer):
            raise ValueError("C guard generation does not yet support mixed floating-point and integer comparisons.")
    return f"({left} {operator} {right})"


def emit_setter_assignment(assignment: BoundAssignment, enum_member: Callable[[str, str], str]) -> str:
    """Render a setter with a range check before any potentially narrowing write."""
    target = f"state_machine->context.{assignment.field_name}"
    expression = assignment.expression
    value = _emit_expression(expression, enum_member)
    datatype = assignment.datatype
    if not isinstance(datatype, SMALPrimitive):
        return f"{target} = {value};"

    limits = []
    source_type = expression.datatype
    temporary_type = "uint64_t" if source_type == SMALPrimitive.UINT64 else "int64_t"
    if datatype.is_integer:
        bounds = integer_range(expression)
        assert bounds is not None
        lower, upper = bounds
        if lower < datatype.min_value:
            limits.append(f"value < {integer_literal(datatype.min_value)}")
        if upper > datatype.max_value:
            limits.append(f"value > {integer_literal(datatype.max_value)}")
    elif datatype == SMALPrimitive.FLOAT32 and source_type == SMALPrimitive.FLOAT64:
        temporary_type = "double"
        limits.append("value < -FLT_MAX || value > FLT_MAX")
    if not limits:
        return f"{target} = {value};"
    return "\n".join(
        (
            "{",
            f"    const {temporary_type} value = {value};",
            f"    if ({' || '.join(limits)})",
            "    {",
            "        SMAL_SETTER_RANGE_ERROR();",
            "        return;",
            "    }",
            f"    {target} = value;",
            "}",
        )
    )
