"""Guard references and definitions."""

from __future__ import annotations

from typing import Annotated, Any, ClassVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictStr, model_validator

import smal.utilities.expressions as SMALExpressions
from smal.utilities.types import Identifier  # noqa: TC001 - Pydantic requires this at runtime


class GuardRef(BaseModel):
    """A reference to a guard within a Transition, as opposed to a `GuardDef`, which is the declaration of a guard."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    name: Identifier
    negate: bool = False

    @staticmethod
    def parse(v: Any) -> list[GuardRef]:
        """Parse one or more GuardRef(s) from the given data.

        Args:
            v (Any): The data to parse.

        Returns:
            list[GuardRef]: The parsed guard reference(s).

        """
        if v is None:
            return []
        if isinstance(v, (str, GuardRef)):
            v = [v]
        out = []
        for g in v:
            if isinstance(g, str):
                neg = g.startswith("!")
                out.append(GuardRef(name=g.removeprefix("!"), negate=neg))
            else:
                out.append(g)
        return out


Guards = Annotated[list[GuardRef], BeforeValidator(GuardRef.parse)]
"""A list of guards, automatically parsed and validated upon construction."""


class GuardDef(BaseModel):
    """The declaration of a guard, as opposed to `GuardRef`, which is a reference to one from a transition."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    name: Identifier = Field(description="Guard name.")
    expr: StrictStr | None = Field(
        default=None,
        description=(
            "Boolean expression over context variables, constants and enum members, e.g. 'foo or bar != baz'. "
            "If omitted, the guard depends on something outside the machine's context (a sensor, say), and path analysis treats it as possibly true or false."
        ),
    )
    description: StrictStr | None = Field(default=None, description="Description of the guard.")

    @model_validator(mode="before")
    @classmethod
    def _from_shorthand(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"name": data}
        # Mapping shorthand: {GuardName: "expression"}
        if isinstance(data, dict) and len(data) == 1:
            key, value = next(iter(data.items()))
            if key not in cls.model_fields and isinstance(value, str):
                return {"name": key, "expr": value}
        return data

    @model_validator(mode="after")
    def _check_expression(self) -> GuardDef:
        if self.expr is not None:
            SMALExpressions.parse(self.expr)  # Raises ValueError on invalid syntax
        return self
