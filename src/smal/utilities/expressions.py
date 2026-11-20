"""A small, safe expression language for guard conditions and context assignments.

The syntax is a subset of Python: `and`, `or`, `not`, the comparisons `==`, `!=`, `<`, `<=`, `>` and `>=`, `+`, `-`, `*`,
parentheses, `True`/`False`, integer literals, and names.

A name evaluates to the value of the context variable or constant with that name, if there is one. Any other name is an
enum member, which evaluates to its own name as a string. So with `foo` currently set to `bar`, the
expression `foo != none` compares the string "bar" with the string "none".

Nothing here is ever passed to `eval`: expressions are parsed with `ast` and only the node types above are accepted.
"""

from __future__ import annotations

import ast
import operator
from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

Value = bool | int | str

_COMPARISONS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}
_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul}


@cache
def parse(source: str) -> ast.expr:
    """Parse and validate an expression.

    Args:
        source (str): The expression text.

    Raises:
        ValueError: If the text is not valid syntax or uses anything outside the supported subset.

    Returns:
        ast.expr: The validated expression tree.

    """
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid expression {source!r}: {exc.msg}.") from exc
    _validate(tree.body, source)
    return tree.body


def _validate(node: ast.expr, source: str) -> None:
    if isinstance(node, ast.BoolOp):
        children = node.values
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.Not, ast.USub)):
        children = [node.operand]
    elif isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        children = [node.left, node.right]
    elif isinstance(node, ast.Compare) and all(type(op) in _COMPARISONS for op in node.ops):
        children = [node.left, *node.comparators]
    elif (isinstance(node, ast.Constant) and isinstance(node.value, (bool, int))) or isinstance(node, ast.Name):
        return
    else:
        raise ValueError(f"Unsupported syntax ({type(node).__name__}) in expression {source!r}.")
    for child in children:
        _validate(child, source)


def referenced_names(node: ast.expr) -> set[str]:
    """Get every name an expression refers to (context variables, constants and enum members).

    Args:
        node (ast.expr): A tree returned by `parse`.

    Returns:
        set[str]: The referenced names.

    """
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def bare_name(source: str) -> str | None:
    """Get the name if the whole expression is a single bare name, e.g. an enum member such as `full`.

    Args:
        source (str): The expression text.

    Returns:
        str | None: The name, or None if the expression is anything more complex.

    """
    node = parse(source)
    return node.id if isinstance(node, ast.Name) else None


def evaluate(node: ast.expr, env: Mapping[str, Value]) -> Value:
    """Evaluate an expression tree.

    Args:
        node (ast.expr): A tree returned by `parse`.
        env (Mapping[str, Value]): Values of the context variables and constants. Names not in it are enum members.

    Raises:
        ValueError: If the expression mixes incompatible types, such as comparing a number with an enum member.

    Returns:
        Value: The result.

    """
    try:
        return _evaluate(node, env)
    except TypeError as exc:
        raise ValueError(f"Cannot evaluate expression {ast.unparse(node)!r}: {exc}.") from exc


def evaluate_source(source: str, env: Mapping[str, Value]) -> Value:
    """Parse and evaluate expression text.

    Args:
        source (str): The expression text.
        env (Mapping[str, Value]): Values of the context variables and constants.

    Returns:
        Value: The result.

    """
    return evaluate(parse(source), env)


def _evaluate(node: ast.expr, env: Mapping[str, Value]) -> Value:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return env.get(node.id, node.id)
    if isinstance(node, ast.BoolOp):
        results = (_evaluate(v, env) for v in node.values)
        return all(results) if isinstance(node.op, ast.And) else any(results)
    if isinstance(node, ast.UnaryOp):
        operand = _evaluate(node.operand, env)
        return (not operand) if isinstance(node.op, ast.Not) else -operand
    if isinstance(node, ast.BinOp):
        return _BINARY[type(node.op)](_evaluate(node.left, env), _evaluate(node.right, env))
    if isinstance(node, ast.Compare):
        left = _evaluate(node.left, env)
        for op, comparator in zip(node.ops, node.comparators, strict=True):
            right = _evaluate(comparator, env)
            if not _COMPARISONS[type(op)](left, right):
                return False
            left = right
        return True
    raise ValueError(f"Unsupported node {type(node).__name__}.")  # Unreachable for trees returned by `parse`


# TODO: Allow code generation in various languages (start with C) to convert these expressions to real code
