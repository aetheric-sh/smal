"""Module defining the StateMachine model and related classes for representing state machines, including their states, transitions, events, and associated metadata."""

from __future__ import annotations  # Until Python 3.14

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, ClassVar, TypeAlias

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Self

from smal.schemas.command import Command  # noqa: TC001 - Move application import to TYPE_CHECKING block
from smal.schemas.enumeration import Enumeration  # noqa: TC001 - Move application import to TYPE_CHECKING block
from smal.schemas.error import Error
from smal.schemas.event import Event
from smal.schemas.state import State, StateType
from smal.schemas.struct import Struct  # noqa: TC001 - Move application import to TYPE_CHECKING block
from smal.schemas.transition import Transition, TransitionMapShorthand  # noqa: TC001 - Move application import to TYPE_CHECKING block
from smal.schemas.utilities import IdentifierValidationMixin, SemverValidationMixin
from smal.utilities import constants as SMALConstants
from smal.utilities.corrections import ALL_CORRECTIONS
from smal.utilities.rules import ALL_RULES


class StateMachine(IdentifierValidationMixin, SemverValidationMixin, BaseModel):
    """Schema defining a SMAL state machine, defined by a .smal file."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,  # So class can be instantiated with real variable names OR aliases
    )

    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("machine",)
    SEMVER_FIELDS: ClassVar[tuple[str]] = ("version",)

    name: str = Field(..., alias="machine", description="Name of this state machine.")
    version: str = Field(..., description="Semantic version (major.minor.patch) of this state machine.")
    states: list[State] = Field(..., description="States associated with this state machine.")
    events: list[Event] = Field(default_factory=list, description="Events associated with this state machine, if any.")
    commands: list[Command] = Field(default_factory=list, description="Commands associated with this state machine, if any.")
    errors: list[Error] = Field(default_factory=list, description="Errors associated with this state machine, if any.")
    constants: dict[str, str | int] = Field(default_factory=dict, description="Constants to define for this state machine, if any.")
    transitions: list[Transition] = Field(default_factory=list, description="State transitions associated with this state machine, if any.")
    enums: list[Enumeration] = Field(default_factory=list, description="Enumerations to define for this state machine, if any.")
    structs: list[Struct] = Field(default_factory=list, description="Structures to define for this state machine, if any.")
    debug: Struct | None = Field(default=None, description="Debugging structure associated with this state machine, if any.")
    description: str | None = Field(default=None, description="Description of the state machine.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Any arbitrary metadata you want to make available to code generation templates.")

    @property
    def adjacency_list(self) -> dict[str, list[str]]:
        """Get the adjacency list for this state machine, where keys are source state names and values are lists of target state names.

        Returns:
            dict[str, list[str]]: The adjacency list representing the transitions between states in this state machine.

        """
        return self._adj

    @property
    def root_state(self) -> State | None:
        """Get the root state of this state machine, which is the unique state that is not a substate of any other state and has no incoming transitions.

        NOTE: Not all state machines are guaranteed to have a root state, for example, an indefinitely-running state machine that always lands back in its initial state.

        No state machine is allowed to have more than one root state, as that would violate the tree structure requirement for the state hierarchy.

        Returns:
            State | None: The root State object of this state machine, or None if no root state exists.

        """
        roots = [s for s in self.states if not s.is_substate and len(self.get_incoming_transitions(s)) == 0]
        match len(roots):
            case 0:
                return None
            case 1:
                return roots[0]
            case _:
                raise ValueError(f"StateMachine '{self.name}' has multiple root states: {', '.join(s.name for s in roots)}. A state machine must have exactly one root state.")

    @property
    def initial_state(self) -> State:
        """Get the initial state of this state machine, which is the unique state that is not a substate of any other state and has type INITIAL.

        Returns:
            State: The initial State object of this state machine.

        """
        initial_states = [s for s in self.states if not s.is_substate and s.type == StateType.INITIAL]
        match len(initial_states):
            case 0:
                raise ValueError(
                    f"StateMachine '{self.name}' has no root initial state. A state machine must have exactly one root initial state (type: INITIAL and not a substate).",
                )
            case 1:
                return initial_states[0]
            case _:
                raise ValueError(
                    f"StateMachine '{self.name}' has multiple root initial states: {', '.join(s.name for s in initial_states)}."
                    " A state machine must have exactly one root initial state (type: INITIAL and not a substate).",
                )

    @model_validator(mode="before")
    @classmethod
    def normalize_shorthand_input(cls, v: Any) -> Any:
        """Normalize any cross-machine shorthand input before any other validation occurs.

        For example, events that are inferred from transitions but not explicitly defined in the events section.

        This allows users to write more concise SMAL files.

        """
        if not isinstance(v, dict):
            return v
        # First, we need to normalize shorthand transitions
        raw_transitions = v.get("transitions")
        if raw_transitions is None:
            return v
        # Normalize transition map -> list[Transition]
        if isinstance(raw_transitions, dict):
            normalized_transitions = TransitionMapShorthand(transitions=raw_transitions).to_transitions()
            v["transitions"] = normalized_transitions
        else:
            normalized_transitions = raw_transitions
        # Infer events from transitions if not explicitly defined
        events = v.get("events", [])
        if not events:
            inferred_evt_names: list[str] = []
            for t in normalized_transitions:
                if isinstance(t, Transition):
                    inferred_evt_names.append(t.evt)
                elif isinstance(t, dict) and "evt" in t:
                    inferred_evt_names.append(t["evt"])
            v["events"] = list(dict.fromkeys(inferred_evt_names))  # Remove duplicates while preserving order
        # Done
        return v

    @field_validator("states", mode="before")
    @classmethod
    def expand_shorthand_states(cls, v: list[str | dict[str, Any]] | None) -> list[State]:
        """Expand all short-hand defined states into their full object notation.

        Args:
            v (Any): The input value for the states field, which can be a list of state names (str) or state definitions (dict).

        Returns:
            list[State]: A list of State objects.

        """
        if v is None:
            return []
        return [State.from_shorthand(s) for s in v]

    @field_validator("events", mode="before")
    @classmethod
    def expand_shorthand_events(cls, v: list[str | dict[str, Any]] | None) -> list[Event]:
        """Expand all short-hand defined events into their full object notation.

        Args:
            v (list[str  |  dict[str, Any]] | None): The input value for the events field, which can be a list of event names (str) or event definitions (dict).

        Returns:
            list[Event]: A list of Event objects.

        """
        if v is None:
            return []
        return [Event.from_shorthand(e) for e in v]

    @field_validator("errors", mode="before")
    @classmethod
    def expand_shorthand_errors(cls, v: list[str | dict[str, Any]] | None) -> list[Error]:
        """Expand all short-hand defined errors into their full object notation.

        Args:
            v (list[str  |  dict[str, Any]] | None): The input value for the errors field, which can be a list of error names (str) or error definitions (dict).

        Returns:
            list[Error]: A list of Error objects.

        """
        if v is None:
            return []
        return [Error.from_shorthand(e) for e in v]

    @model_validator(mode="after")
    def enforce_monotonic_ids(self) -> Self:
        """Enforce that all objects that have an ID (States, Events, Errors, etc.) are defined as monotonically increasing IDs across the set of those objects.

        Returns:
            Self: The validated StateMachine instance with monotonic IDs enforced.

        """

        def enforce_monotonicity_helper(objects: list[State] | list[Error] | list[Event]) -> None:
            obj_type = type(objects[0]).__name__ if objects else "Object"
            ids = [o.id for o in objects]
            if any(i is None for i in ids):
                logging.debug("StateMachine '%s': Some %ss are missing IDs. Assigning fresh monotonic IDs based on order of definition.", self.name, obj_type)
                for idx, obj in enumerate(objects):
                    obj.id = idx
                    logging.debug("StateMachine '%s': Assigned ID %d to %s '%s'.", self.name, idx, obj_type, obj.name)
                return
            sorted_ids = sorted(ids)
            expected_ids = list(range(len(objects)))
            if sorted_ids != expected_ids:
                raise ValueError(f"StateMachine '{self.name}': Object IDs must be monotonically increasing starting from 0. Found IDs: {ids}")
            return

        # Enforce monotonic IDs for states, events and errors
        enforce_monotonicity_helper(self.states)
        enforce_monotonicity_helper(self.events)
        enforce_monotonicity_helper(self.errors)
        # Done
        return self

    @model_validator(mode="after")
    def enforce_unique_names(self) -> Self:
        """Enforce that all named objects (States, Events, Errors, etc.) are defined with globally unique names.

        Returns:
            Self: The validated StateMachine instance with unique names enforced.

        """
        name_to_objects: dict[str, list[Any]] = defaultdict(list)
        for state in self.states:
            name_to_objects[state.name].append(state)
        for event in self.events:
            name_to_objects[event.name].append(event)
        for error in self.errors:
            name_to_objects[error.name].append(error)
        duplicates = {name: objs for name, objs in name_to_objects.items() if len(objs) > 1}
        if duplicates:
            duplicate_messages = []
            for name, objs in duplicates.items():
                obj_types = ", ".join(type(o).__name__ for o in objs)
                duplicate_messages.append(f"Name '{name}' is used by multiple objects of types: {obj_types}")
            raise ValueError(f"StateMachine '{self.name}': Duplicate names found across objects. " + "; ".join(duplicate_messages))
        return self

    @model_validator(mode="after")
    def resolve_composite_transitions(self) -> Self:
        """Resolve any transitions that directly utilize a composite state to instead target that composite's internal initial substate.

        Returns:
            Self: The validated StateMachine instance with composite transition targets resolved.

        """
        for t in self.transitions:
            # We want to consider transitions that use a composite state as a source as well as a target
            src_state = self.get_state(t.src)
            if src_state.type == StateType.COMPOSITE:
                initial_substate_name = src_state.initial_substate
                logging.warning(
                    "StateMachine '%s': Transition from composite state '%s' detected. Redirecting from internal initial substate '%s'...",
                    self.name,
                    t.src,
                    initial_substate_name,
                )
                t.set_original_src(t.src)
                t.src = initial_substate_name
            # Targets...
            tgt_state = self.get_state(t.tgt)
            if tgt_state.type == StateType.COMPOSITE:
                initial_substate_name = tgt_state.initial_substate
                logging.warning(
                    "StateMachine '%s': Transition from '%s' to composite state '%s' detected. Redirecting to internal initial substate '%s'...",
                    self.name,
                    t.src,
                    t.tgt,
                    initial_substate_name,
                )
                t.set_original_tgt(t.tgt)
                t.tgt = initial_substate_name
        return self

    @model_validator(mode="after")
    def enforce_valid_transition_references(self) -> Self:
        """Enforce that all transition references are made to valid, existing objects within the state machine.

        Returns:
            Self: The validated StateMachine instance with valid transition references enforced.

        """
        state_map = self.flatten(self.states)
        event_names = {e.name for e in self.events}
        for t in self.transitions:
            if t.src not in state_map:
                raise ValueError(f"StateMachine '{self.name}': Transition from '{t.src}' references a state that does not exist.")
            if t.tgt not in state_map:
                raise ValueError(f"StateMachine '{self.name}': Transition to '{t.tgt}' references a state that does not exist.")
            if t.evt not in event_names:
                raise ValueError(f"StateMachine '{self.name}': Transition event '{t.evt}' references an event that does not exist.")
            if t.tgt_entry_evt is not None and t.tgt_entry_evt not in event_names:
                raise ValueError(f"StateMachine '{self.name}': Transition target entry event '{t.tgt_entry_evt}' references an event that does not exist.")
        return self

    @model_validator(mode="after")
    def validate_simple_structural_invariants(self) -> Self:
        """Validate simple structural invariants for the state machine.

        Examples:
        - At least one state is defined.
        - At least one root initial state is defined (type: INITIAL and not a substate).
        - No more than one root initial state is defined (type: INITIAL and not a substate).

        Raises:
            ValueError: If no states are defined.
            ValueError: If no root initial state is defined.
            ValueError: If multiple root initial states are defined.

        Returns:
            Self: The validated StateMachine instance with structural invariants enforced.

        """
        if not self.states:
            raise ValueError(f"StateMachine '{self.name}' must have at least one state defined.")
        root_initial_states = [s for s in self.states if s.type == StateType.INITIAL and not s.is_substate]
        match len(root_initial_states):
            case 0:
                raise ValueError(f"StateMachine '{self.name}' must have at least one root initial state defined (type: INITIAL and not a substate).")
            case 1:
                pass  # Valid
            case _:
                raise ValueError(
                    f"StateMachine '{self.name}' must have exactly one root initial state defined (type: INITIAL and not a substate)."
                    f" Found: {', '.join(s.name for s in root_initial_states)}",
                )
        return self

    def model_post_init(self, _context: Any) -> None:
        """Run model post-initialization on this StateMachine.

        Args:
            _context (Any): The validation context provided by Pydantic, which is not used in this method but is required by the signature.

        """
        # Apply all corrections before validating
        for correction in ALL_CORRECTIONS:
            logging.info("Applying correction: %s", correction.name)
            correction.pre_application(self)
            correction.apply(self)
            logging.info("Correction '%s' applied", correction.name)
            correction.post_application(self)
        # Build adjacency lists
        self._adj: dict[str, list[str]] = defaultdict(list)
        for t in self.transitions:
            self._adj[t.src].append(t.tgt)
        # Build reverse adjacency lists
        self._adj_rev: dict[str, list[str]] = defaultdict(list)
        # Add implicit composite state entry edges
        # Precompute least common ancestors
        # Evaluate all rules to validate
        for rule in ALL_RULES:
            logging.info("Evaluating rule: %s", rule.name)
            rule.pre_evaluation(self)
            rule.evaluate(self)
            logging.info("Rule '%s' satisfied", rule.name)
            rule.post_evaluation(self)

    @staticmethod
    def flatten(states: list[State]) -> dict[str, State]:
        """Get a flattened dictionary of all states (including substates) from the given list.

        Args:
            states (list[State]): The list of states to flatten, which may include composite states with substates.

        Returns:
            dict[str, State]: The flattened dictionary mapping state names to State objects, including all substates.

        """
        flat: dict[str, State] = {}
        for s in states:
            flat[s.name] = s
            if s.substates:
                flat.update(StateMachine.flatten(s.substates))
        return flat

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        """Instantiate a StateMachine/SMALFile from the file at the given path.

        Args:
            path (str | Path): The file path to read the state machine definition from. Must have a supported SMAL file extension.

        Raises:
            ValueError: If the file does not have a supported SMAL file extension.
            FileNotFoundError: If the file does not exist.

        Returns:
            Self: The StateMachine instance created from the file.

        """
        path = Path(path)
        try:
            if not SMALConstants.SupportedFileExtensions.is_smal_file(path, check_exists=True):
                raise ValueError(f"SMAL file must have one of the following extensions: {', '.join(SMALConstants.SupportedFileExtensions.all())}")
        except FileNotFoundError:  # noqa: TRY203 - Remove exception handler, error is immediately re-raised
            raise
        yaml_data = path.read_text(encoding="utf-8")
        model_data = yaml.safe_load(yaml_data)
        model = cls.model_validate(model_data)
        return model

    def get_state(self, name: str) -> State:
        """Get a state by name from this state machine.

        Args:
            name (str): The name of the state to retrieve.

        Returns:
            State: The State object with the given name.

        """
        state_map = self.flatten(self.states)
        if name not in state_map:
            raise KeyError(f"State '{name}' not found in state machine '{self.name}'.")
        return state_map[name]

    def get_incoming_transitions(self, state: str | State) -> list[Transition]:
        """Get all incoming transitions to the given state.

        Args:
            state (str | State): The name of the target state or the State object itself.

        Returns:
            list[Transition]: A list of Transition objects that have the given state as their target.

        """
        state_name = state if isinstance(state, str) else state.name
        return [t for t in self.transitions if t.tgt == state_name]

    def get_outgoing_transitions(self, state: str | State) -> list[Transition]:
        """Get all outgoing transitions from the given state.

        Args:
            state (str | State): The name of the source state or the State object itself.

        Returns:
            list[Transition]: A list of Transition objects that have the given state as their source.

        """
        state_name = state if isinstance(state, str) else state.name
        return [t for t in self.transitions if t.src == state_name]

    def to_file(
        self,
        path: str | Path,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = True,
        exclude_computed_fields: bool = False,
        sort_keys: bool = False,
        indent: int = 2,
    ) -> None:
        """Serialize this StateMachine to a SMAL file.

        Args:
            path (str | Path): The file path to write the state machine definition to. Must have a supported SMAL file extension.
            exclude_unset (bool, optional): Whether to exclude unset fields from the output. Defaults to False.
            exclude_defaults (bool, optional): Whether to exclude fields with default values from the output. Defaults to False.
            exclude_none (bool, optional): Whether to exclude fields with None values from the output. Defaults to True.
            exclude_computed_fields (bool, optional): Whether to exclude computed fields from the output. Defaults to False.
            sort_keys (bool, optional): Whether to sort the keys in the output. Defaults to False.
            indent (int, optional): The number of spaces to use for indentation in the output. Defaults to 2.

        Raises:
            ValueError: If the file does not have a supported SMAL file extension.

        """
        # First, we need to restore any modified transitions back to their original composite states if they were redirected to initial substates during validation
        for t in self.transitions:
            if t.original_src is not None:
                t.src = t.original_src
                t.set_original_src(None)
            if t.original_tgt is not None:
                t.tgt = t.original_tgt
                t.set_original_tgt(None)
        # Now we can proceed with the file generation as normal
        path = Path(path)
        if not SMALConstants.SupportedFileExtensions.is_smal_file(path, check_exists=False):
            raise ValueError(f"SMAL file must have one of the following extensions: {', '.join(SMALConstants.SupportedFileExtensions.all())}")
        model_data = self.model_dump(exclude_unset=exclude_unset, exclude_defaults=exclude_defaults, exclude_none=exclude_none, exclude_computed_fields=exclude_computed_fields)
        yaml_data = yaml.safe_dump(model_data, sort_keys=sort_keys, indent=indent)
        path.write_text(yaml_data, encoding="utf-8")


SMALFile: TypeAlias = StateMachine
