"""Module defining the State model and related classes for representing states in a state machine, including their types, properties, and validation rules."""

from __future__ import annotations  # Until Python 3.14

import logging
from enum import Enum
from functools import cached_property
from typing import Any, ClassVar

from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator
from typing_extensions import Self

from smal.schemas.utilities import IdentifierValidationMixin


class StateType(str, Enum):
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
    def default_metadata(self) -> dict[str, Any]:
        """Get the default metadata for this StateType.

        Returns:
            dict[str, Any]: The default metadata for this StateType, which may include graphviz rendering attributes and other relevant information.

        """
        return {
            StateType.SIMPLE: {"shape": "box", "style": "rounded"},
            StateType.COMPOSITE: {"shape": "box", "style": "rounded"},
            StateType.INITIAL: {"shape": "circle"},
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
        """Get whether or not this StateType represents a pseudostate, e.g. a non-behavioral state which only serves a structural or control-flow purpose in the state machine.

        Returns:
            bool: True if this StateType is a pseudostate, False otherwise.

        """
        return not self.is_behavioral_state

    @cached_property
    def shape(self) -> str:
        """Get the graphviz rendering shape of this StateType from its metadata.

        Returns:
            str: The graphviz shape for this StateType, or an empty string if no shape is defined in the metadata.

        """
        return self.default_metadata.get("shape", "")

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

    def get_metadata(self, **overrides: Any) -> dict[str, Any]:
        """Get the metadata of this StateType, applying any given overrides over the defaults.

        Returns:
            dict[str, Any]: The metadata for this StateType, with any provided overrides applied on top of the defaults.

        """
        default_metadata = self.default_metadata.copy()
        default_metadata.update(overrides)
        return default_metadata


class State(BaseModel, IdentifierValidationMixin):
    """Model describing a state in a state machine."""

    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("name",)

    name: str = Field(...)
    id: int | None = Field(default=None)
    type: StateType = Field(default=StateType.SIMPLE)
    substates: list[State] = Field(default_factory=list)
    description: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)
    _parent_name: str | None = PrivateAttr(default=None)

    @property
    def initial_substate(self) -> State:
        """Get the initial substate of this composite state.

        Raises:
            ValueError: If this state is not composite and does not have substates.
            ValueError: If this composite state does not have an initial substate defined.
            ValueError: If this composite state has multiple initial substates defined, which is not allowed

        Returns:
            State: The initial substate of this composite state.

        """
        if not self.is_composite:
            raise ValueError(f"State '{self.name}' is not composite and does not have substates.")
        initial_substates = [ss for ss in self.substates if ss.type == StateType.INITIAL]
        match len(initial_substates):
            case 0:
                raise ValueError(f"Composite state '{self.name}' does not have an initial substate defined.")
            case 1:
                return initial_substates[0]
            case _:
                raise ValueError(f"Composite state '{self.name}' has multiple initial substates defined, which is not allowed.")

    @property
    def is_composite(self) -> bool:
        """Get whether or not this state is composite, e.g. it contains substates.

        Returns:
            bool: True if this state is composite, False otherwise.

        """
        return self.type == StateType.COMPOSITE and self.substates

    @property
    def is_substate(self) -> bool:
        """Get whether or not this state is a substate, e.g. it has a parent state.

        Returns:
            bool: True if this state is a substate, False otherwise.

        """
        return self.parent_name is not None

    @property
    def parent_name(self) -> str | None:
        """Get the name of the parent state of this state, if it is a substate.

        Returns:
            str | None: The name of the parent state if this state is a substate, or None if this state does not have a parent.

        """
        return self._parent_name

    def set_parent(self, parent: State) -> None:
        """Set the parent of this state.

        Args:
            parent (State): The parent state to set for this state.

        """
        self._parent_name = parent.name

    @classmethod
    def from_shorthand(cls, data: Any) -> State:
        """Create a State instance from a short-hand representation in data.

        Args:
            data (Any): The input data for the state, which can be a string (state name) or a dictionary with state properties.

        Raises:
            ValueError: If the input data is not a string or a dictionary.

        Returns:
            State: The State instance created from the short-hand representation.

        """
        if isinstance(data, str):
            return cls(name=data)
        if isinstance(data, dict):
            return cls.model_validate(data)
        raise ValueError(f"Invalid short-hand state representation: {data!r}. Expected a string or a dictionary.")

    @field_validator("substates", mode="before")
    @classmethod
    def expand_shorthand_substates(cls, v: Any) -> list[State]:
        """Expand all short-hand (e.g. ones defined simply by name instead of as an object) substates into their full form.

        Args:
            v (Any): The incoming data for the substates field, which may be a list of strings, a list of dicts, or None.

        Raises:
            TypeError: If any substate is not a string or a dictionary.

        Returns:
            list[State]: The list of expanded substates.

        """
        if v is None:
            return []  # Substates are optional, so None is treated as an empty list
        return [State.from_shorthand(ss) for ss in v]

    @model_validator(mode="before")
    @classmethod
    def derive_state_type(cls, v: Any) -> Any:
        """Derive the type of this state either by its explicitly provided 'type' field or by recognizing a type suffix in its name.

        If both are provided, the explicit 'type' field takes precedence.

        Args:
            v (Any): The incoming data for the state, which should be a dictionary containing at least a 'name' field and optionally a 'type' field.

        Raises:
            ValueError: If the state definition is missing the required 'name' field.
            ValueError: If the state name ends with multiple recognized type suffixes, making it ambiguous.

        Returns:
            Any: The updated state definition with the derived type, if applicable.

        """
        if not isinstance(v, dict):
            return v  # Only process dict inputs, which are expected for State definitions
        state_type = v.get("type", None)
        if state_type is not None:
            return v  # Always prioritize an explicitly provided type
        name = v.get("name", "")
        if not name:
            raise ValueError("State definition missing required field 'name'.")
        shorthanded_types = {st for st in StateType if name.lower().endswith(st.shorthand_suffix.lower())}
        match len(shorthanded_types):
            case 0:
                pass  # No recognized type suffixes, leave type as default
            case 1:
                shorthanded_type = next(iter(shorthanded_types))
                v["type"] = shorthanded_type.value  # Set type based on the single recognized suffix
                v["name"] = name[: -len(shorthanded_type.shorthand_suffix)]  # Strip the suffix from the name
                if not v["name"]:
                    raise ValueError(f"State name '{name}' cannot consist only of a shorthand suffix.")
            case _:
                raise ValueError(f"State name '{name}' ends with multiple recognized type suffixes. Cannot unambiguously derive type from name.")
        return v

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
                raise ValueError(f"Substates of State '{self.name}' must have unique, non-negative, and monotonically increasing IDs starting from 0. Found IDs: {substate_ids}")
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
