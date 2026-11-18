"""Module defining the State model and related classes for representing states in a state machine, including their types, properties, and validation rules."""

from __future__ import annotations  # Until Python 3.14

import logging
from enum import StrEnum
from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, PrivateAttr, StrictInt, StrictStr, model_validator

if TYPE_CHECKING:
    from smal.utilities.types import Identifier


class StateType(StrEnum):
    """Enumeration of possible state types in a state machine, including both behavioral states and pseudostates."""

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
        """Get whether or not this StateType represents a behavioral state, e.g. a state which can have associated behavior and semantics in the state machine.

        Returns:
            bool: True if this StateType is a behavioral state, False otherwise.

        """
        match self:
            case StateType.SIMPLE | StateType.COMPOSITE:
                return True
            case _:
                return False

    @cached_property
    def is_pseudo_state(self) -> bool:
        """Get whether or not this StateType represents a pseudostate, e.g. a non-behavioral state which only serves a structural or control-flow purpose.

        Returns:
            bool: True if this StateType is a pseudostate, False otherwise.

        """
        return not self.is_behavioral_state

    @cached_property
    def shorthand_suffix(self) -> str:
        """Get the shorthand suffix identifier for this StateType, to be appended to the State.name field in SMAL files.

        Returns:
            str: The shorthand suffix for this StateType, or an empty string if this StateType does not have a shorthand suffix.

        """
        return {
            StateType.SIMPLE: "_s",
            StateType.COMPOSITE: "_c",
            StateType.INITIAL: "_i",
            StateType.TERMINAL: "_t",
            StateType.ENTRY: "_en",
            StateType.EXIT: "_ex",
            StateType.ERROR: "_er",
            StateType.DECISION: "_d",
            StateType.JOIN: "_jn",
            StateType.FORK: "_fk",
            StateType.JUNCTION: "_jc",
            StateType.FINAL: "_f",
        }.get(self, "")


class State(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    name: Identifier = Field(description="State name.")
    id: StrictInt | None = Field(default=None, description="Numeric identifier for the state.")
    type: StateType = Field(default=StateType.SIMPLE)
    substates: list[State] = Field(default_factory=list)
    description: StrictStr | None = Field(default=None)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    _parent_name: str | None = PrivateAttr(default=None)

    @property
    def is_composite(self) -> bool:
        return self.type == StateType.COMPOSITE and self.substates

    @property
    def initial_substate(self) -> State:
        if not self.is_composite:
            raise ValueError("State '{self.name}' is not composite and does not have substates.")
        initial_substates = [ss for ss in self.substates if ss.type == StateType.INITIAL]
        match len(initial_substates):
            case 0:
                raise ValueError(f"Composite state '{self.name}' does not have an initial substate defined.")
            case 1:
                return initial_substates[0]
            case _:
                raise ValueError(f"Composite state '{self.name}' has multiple initial substates defined, which is invalid.")

    @property
    def parent_name(self) -> str | None:
        return self._parent_name

    @property
    def is_substate(self) -> bool:
        return self.parent_name is not None

    def set_parent(self, parent: State) -> None:
        self._parent_name = parent.name

    @model_validator(mode="before")
    @classmethod
    def _normalize_input(cls, data: Any) -> Any:
        """Expand the string shorthand and derive the state type from a name suffix.

        This must only rewrite the raw input and never construct a State itself (that would re-enter this validator).
        State instances and invalid input are passed through so Pydantic can handle or report them.
        """
        if isinstance(data, str):
            data = {"name": data}
        if not isinstance(data, dict):
            return data
        data = dict(data)  # Don't mutate the caller's data
        if data.get("type") is not None:
            return data  # Always prioritize an explicitly provided type
        name = data.get("name")
        if not isinstance(name, str) or not name:
            return data  # Pydantic reports the missing/invalid name
        matches = [st for st in StateType if name.lower().endswith(st.shorthand_suffix.lower())]
        match len(matches):
            case 0:
                pass  # No recognized type suffix, leave type as default
            case 1:
                state_type = matches[0]
                stripped = name[: -len(state_type.shorthand_suffix)]
                if not stripped:
                    raise ValueError(f"State name '{name}' cannot consist only of a shorthand suffix.")
                data["type"] = state_type.value
                data["name"] = stripped
            case _:
                raise ValueError(f"State name '{name}' ends with multiple recognized type suffixes. Cannot unambiguously derive type from name.")
        return data

    @model_validator(mode="after")
    def enforce_compositeness(self) -> Self:
        """Enforce that if this state defines substates, it is a well-formed composite state.

        Raises:
            ValueError: If the state has substates but is marked as a pseudostate, which cannot have substates.
            ValueError: If the state has substates but is explicitly marked as a non-composite state.

        Returns:
            Self: The state instance with enforced compositeness rules.

        """
        if self.substates:
            if self.type.is_pseudo_state:
                raise ValueError(f"State '{self.name}' is a pseudostate (type: {self.type.value}) and cannot have substates.")
            if self.type != StateType.COMPOSITE:
                if self.type != State.model_fields["type"].default:
                    raise ValueError(
                        (
                            f"State '{self.name}' defines substates but is marked as a {self.type.value} state instead of a composite state."
                            " Remove substates or redefine as composite to resolve."
                        ),
                    )
                logging.warning("CORRECTION: State '%s' was not designated as a Composite even though it has substates. Automatically correcting...", self.name)
                self.type = StateType.COMPOSITE
            # Ensure all substates are assigned a parent name
            for ss in self.substates:
                ss.set_parent(self)
        return self

    @model_validator(mode="after")
    def enforce_substate_rules(self) -> Self:
        """Enforce that all substates of this state (if applicable) follow validation rules.

        Returns:
            Self: The state instance with validated substates.

        """
        if self.substates:
            for _ss in self.substates:
                pass  # TODO: Run rulesets
        return self

    @model_validator(mode="after")
    def enforce_monotonic_substate_ids(self) -> Self:
        """Validate that all substates have monotonically increasing integer IDs, if applicable.

        Raises:
            ValueError: If substates have IDs that are not unique, non-negative, or monotonically increasing starting from 0.

        Returns:
            Self: The state instance with validated substate IDs.

        """
        if self.substates:
            substate_ids = [ss.id for ss in self.substates]
            if any(sid is None for sid in substate_ids):
                logging.debug(
                    "State '%s': Some substates are missing IDs. Assigning fresh monotonic IDs based on definition order.",
                    self.name,
                )
                for idx, ss in enumerate(self.substates):
                    ss.id = idx
                    logging.debug("State '%s': Auto-assigned ID %s to substate '%s'.", self.name, ss.id, ss.name)
                return self
            sorted_ids = sorted(substate_ids)
            expected = list(range(len(substate_ids)))
            if sorted_ids != expected:
                raise ValueError(
                    f"Substates of State '{self.name}' must have unique, non-negative, and \
                                    monotonically increasing IDs starting from 0. Found IDs: {substate_ids}",
                )
        return self

    @model_validator(mode="after")
    def validate_simple_structure_invariants(self) -> Self:
        """Validate simple structural invariants for this state.

        Examples:
        - If this state is a composite state, it must have exactly 1 initial substate.

        Returns:
            Self: The state instance with validated structural invariants.

        """

        def helper(states: list[State]) -> None:
            for s in states:
                if s.is_composite:
                    initial_substates = [ss for ss in s.substates if ss.type == StateType.INITIAL]
                    match len(initial_substates):
                        case 0:
                            raise ValueError(f"Composite state '{s.name}' does not have an initial substate defined.")
                        case 1:
                            pass  # Valid, exactly one initial substate
                        case _:
                            raise ValueError(f"Composite state '{s.name}' has multiple initial substates defined, which is not allowed.")
                    helper(s.substates)  # Recursively validate substates of this composite state

        helper([self])
        return self


class IllegalStateError(ValueError):
    """Exception raised when an illegal state is encountered during validation or processing of a state machine definition."""

    def __init__(self, message: str, state: State | None = None, state_machine_name: str | None = None) -> None:
        """Initialize the IllegalStateError.

        Args:
            message (str): The error message describing the illegal state condition that was encountered.
            state (State | None, optional): The state instance that caused the error, if applicable. Defaults to None.
            state_machine_name (str | None, optional): The name of the state machine where the error occurred, if applicable. Defaults to None.

        """
        details = []
        if state is not None:
            details.append(f"State: {state.name}")
            details.append(f"Type: {state.type.value}")
            details.append(f"Substate: {state.is_substate} (parent: {state.parent_name})")
        if details:
            message = f"{message}\n" + "\n".join(details)
        if state_machine_name:
            message = f"StateMachine '{state_machine_name}': {message}"
        super().__init__(message)
