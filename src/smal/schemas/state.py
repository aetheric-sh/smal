from __future__ import annotations  # Until Python 3.14

import logging
from enum import Enum
from functools import cached_property
from typing import Any, ClassVar

from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator
from typing_extensions import Self

from smal.schemas.utilities import IdentifierValidationMixin


class StateType(str, Enum):
    # Behavioral states
    SIMPLE = "simple"
    COMPOSITE = "composite"
    # Pseudo states
    INITIAL = "initial"
    TERMINAL = "terminal"
    ENTRY = "entry"
    EXIT = "exit"
    ERROR = "error"
    DECISION = "decision"
    JOIN = "join"
    FORK = "fork"
    JUNCTION = "junction"
    FINAL = "final"

    @cached_property
    def is_behavioral_state(self) -> bool:
        match self:
            case StateType.SIMPLE | StateType.COMPOSITE:
                return True
            case _:
                return False

    @cached_property
    def is_pseudo_state(self) -> bool:
        return not self.is_behavioral_state

    @cached_property
    def default_metadata(self) -> dict[str, Any]:
        return {
            StateType.SIMPLE: {"shape": "box", "style": "rounded"},
            StateType.COMPOSITE: {"shape": "box", "style": "rounded"},
            StateType.INITIAL: {"shape": "point"},
            StateType.TERMINAL: {"shape": "none", "label": "✕", "fontsize": "24"},
            StateType.ENTRY: {"shape": "circle", "color": "green"},
            StateType.EXIT: {"shape": "circle", "color": "red"},
            StateType.ERROR: {"shape": "hexagon"},
            StateType.DECISION: {"shape": "diamond"},
            StateType.JOIN: {"shape": "rect", "width": "1.2", "height": "0.1", "style": "filled", "color": "black", "fillcolor": "black"},
            StateType.FORK: {"shape": "rect", "width": "0.1", "height": "1.2", "style": "filled", "color": "black", "fillcolor": "black"},
            StateType.JUNCTION: {"shape": "point"},
            StateType.FINAL: {"shape": "doublecircle"},
        }.get(self, {})

    @cached_property
    def shape(self) -> str:
        return self.default_metadata.get("shape", "")

    def get_metadata(self, **overrides: Any) -> dict[str, Any]:
        default_metadata = self.default_metadata.copy()
        default_metadata.update(overrides)
        return default_metadata


class State(IdentifierValidationMixin, BaseModel):
    """Schema defining a state within a state machine."""

    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str = Field(..., description="A unique name for the state, which serves as its identifier and may be used in transitions.")
    substates: list[State] = Field(default_factory=list, description="Substates of the state, if any.")
    id: int | None = Field(
        default=None,
        description="A unique integer identifier for the state. If not provided, it may be auto-assigned based on the order of definition or other criteria.",
    )
    description: str | None = Field(default=None, description="A human-readable description of the state.")
    type: StateType = Field(default=StateType.SIMPLE, description="The type of the state, which may affect its behavior and/or visualization.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata associated with rendering this state using Graphviz.")
    _parent_name: str | None = PrivateAttr(default=None)

    @property
    def parent_name(self) -> str | None:
        return self._parent_name

    @property
    def is_substate(self) -> bool:
        return self.parent_name is not None

    @field_validator("substates", mode="before")
    def expand_short_form_substates(cls, v: list[dict | str] | None) -> list[State]:
        if v is None:
            return []
        expanded_substates = []
        for item in v:
            if isinstance(item, str):
                expanded_substates.append(State(name=item))
            elif isinstance(item, dict):
                expanded_substates.append(State.model_validate(item))
            else:
                raise ValueError(f"Invalid state definition: {item}. Must be either a string or a dictionary.")
        return expanded_substates

    @model_validator(mode="after")
    def validate_compositeness(self) -> Self:
        if self.substates:
            if self.type.is_pseudo_state:
                raise ValueError(f"State<{self.name}> is a pseudostate (type: {self.type.value}) and cannot have substates.")
            if not self.type == StateType.COMPOSITE:
                if self.type != State.model_fields["type"].default:
                    raise ValueError(
                        f"State<{self.name}> defines substates but is marked as a {self.type.value} instead of a composite state. Found '{self.type.value}'. Remove substates or redefine as composite to resolve.",
                    )
                logging.warning("State '%s' was not designated as a Composite even though it has substates. Automatically correcting...", self.name)
            # Ensure all substates are assigned a parent name
            for ss in self.substates:
                ss.set_parent(self)
        return self

    @model_validator(mode="after")
    def validate_monotonic_substate_ids(self) -> Self:
        # Extract IDs
        ids = [s.id for s in self.substates]
        # Case 1: Some IDs missing → assign all fresh IDs
        if any(i is None for i in ids):
            logging.debug(
                "State<%s>: Some substates are missing IDs. Assigning fresh monotonic IDs based on definition order.",
                self.name,
            )
            for idx, s in enumerate(self.substates):
                s.id = idx
                logging.debug("State<%s>: Auto-assigned ID %s to substate '%s'.", self.name, s.id, s.name)
            return self
        # Case 2: All IDs present → validate monotonicity
        sorted_ids = sorted(ids)
        expected = list(range(len(ids)))
        if sorted_ids != expected:
            raise ValueError(f"State<{self.name}>: Substate IDs must be monotonic and contiguous starting at 0. Found {ids}, expected {expected}.")
        return self

    def detect_cycles(self) -> list[str]:
        cycles: list[str] = []

        def helper(state, parent_chain):
            if state in parent_chain:
                names = [s.name for s in parent_chain + [state]]
                cycles.append(" → ".join(names))
                return
            for ss in state.substates:
                helper(ss, parent_chain + [state])

        helper(self, [])
        return cycles

    def set_parent(self, parent: State) -> None:
        self._parent_name = parent.name

    @property
    def is_composite(self) -> bool:
        """Get whether or not this state is composite, e.g. it contains substates.

        Returns:
            bool: True if this state is composite, False otherwise.

        """
        return self.type == StateType.COMPOSITE


class IllegalStateError(ValueError):
    def __init__(self, message: str, state: State | None = None, state_machine_name: str | None = None) -> None:
        details = []
        if state is not None:
            details.append(f"State: {state.name}")
            details.append(f"Type: {state.type.value}")
            details.append(f"Substate: {state.is_substate} (parent: {state.parent_name})")
        if details:
            message = f"{message}\n" + "\n".join(details)
        if state_machine_name:
            message = f"StateMachine<{state_machine_name}>: {message}"
        super().__init__(message)
