from __future__ import annotations  # Until Python 3.14

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, ClassVar, TypeAlias

import yaml
from pydantic import BaseModel, Field, field_validator
from typing_extensions import Self

from smal.schemas.command import Command
from smal.schemas.enumeration import Enumeration
from smal.schemas.error import Error
from smal.schemas.event import Event
from smal.schemas.state import State
from smal.schemas.struct import Struct
from smal.schemas.transition import Transition
from smal.schemas.utilities import IdentifierValidationMixin, SemverValidationMixin
from smal.utilities import constants as SMALConstants
from smal.utilities.rules import ALL_RULES


class StateMachine(IdentifierValidationMixin, SemverValidationMixin, BaseModel):
    """Schema defining a SMAL state machine, defined by a .smal file."""

    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("machine",)
    SEMVER_FIELDS: ClassVar[tuple[str]] = ("version",)

    machine: str = Field(..., description="Name of this state machine.")
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

    def model_post_init(self, _context: Any) -> None:
        # Build adjacency lists
        self._adj: dict[str, list[str]] = defaultdict(list)
        self._adj_rev: dict[str, list[str]] = defaultdict(list)
        for t in self.transitions:
            self._adj[t.src_state].append(t.tgt_state)
        # Add implicit composite state entry edges
        # for cs in [s for s in self.states if s.type == StateType.COMPOSITE]:
        #     pass
        # Build reverse adjacency lists
        # Precompute entry/exit sequences
        # Precompute least common ancestors
        # Precompute allowed transitions
        # Precompute default entry paths
        # Run all evaluation rules
        for rule in ALL_RULES:
            logging.info("Evaluating rule: %s", rule.name)
            rule.pre_evaluation(self)
            rule.evaluate(self)
            logging.info("Rule '%s' satisfied", rule.name)
            rule.post_evaluation(self)

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        path = Path(path)
        try:
            if not SMALConstants.SupportedFileExtensions.is_smal_file(path, check_exists=True):
                raise ValueError(f"SMAL file must have one of the following extensions: {', '.join(SMALConstants.SupportedFileExtensions.all())}")
        except FileNotFoundError:
            raise
        yaml_data = path.read_text(encoding="utf-8")
        model_data = yaml.safe_load(yaml_data)
        model = cls.model_validate(model_data)
        return model

    def get_adjacency_list(self, reversed: bool = False) -> dict[str, list[str]]:
        return self._adj_rev if reversed else self._adj

    def get_flattened_states(self) -> dict[str, State]:
        return self._flatten_states(self.states)

    def get_incoming_transitions(self, state: State) -> list[Transition]:
        return [t for t in self.transitions if t.tgt_state == state.name]

    def get_outgoing_transitions(self, state: State) -> list[Transition]:
        return [t for t in self.transitions if t.src_state == state.name]

    def get_root(self) -> State:
        roots = [s for s in self.states if len(self.get_incoming_transitions(s)) == 0]
        if not roots:
            raise ValueError("State machine is empty.")
        if len(roots) > 1:
            raise ValueError(f"State machine has more than 1 root defined: {', '.join([r.name for r in roots])}")
        return roots[0]

    def get_state(self, name: str) -> State:
        return self.get_flattened_states()[name]

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
        path = Path(path)
        if not SMALConstants.SupportedFileExtensions.is_smal_file(path, check_exists=False):
            raise ValueError(f"SMAL file must have one of the following extensions: {', '.join(SMALConstants.SupportedFileExtensions.all())}")
        model_data = self.model_dump(exclude_unset=exclude_unset, exclude_defaults=exclude_defaults, exclude_none=exclude_none, exclude_computed_fields=exclude_computed_fields)
        yaml_data = yaml.safe_dump(model_data, sort_keys=sort_keys, indent=indent)
        path.write_text(yaml_data, encoding="utf-8")

    @staticmethod
    def _flatten_states(states: list[State]) -> dict[str, State]:
        flat = {}
        for s in states:
            if s.name in flat:
                raise ValueError(f"Duplicate state name '{s.name}' found in nested states.")
            flat[s.name] = s
            if s.substates:
                nested = SMALFile._flatten_states(s.substates)
                for name, obj in nested.items():
                    if name in flat:
                        raise ValueError(f"Duplicate state name '{s.name}' found in nested states.")
                    flat[name] = obj
        return flat

    @field_validator("states", mode="before")
    def expand_short_form_states(cls, v: list[dict | str]) -> list[State]:
        expanded_states = []
        for item in v:
            if isinstance(item, str):
                expanded_states.append(State(name=item))
            elif isinstance(item, dict):
                expanded_states.append(State.model_validate(item))
            else:
                raise ValueError(f"Invalid state definition: {item}. Must be either a string or a dictionary.")
        return expanded_states

    @field_validator("events", mode="before")
    def expand_short_form_events(cls, v: list[dict | str]) -> list[Event]:
        expanded_events = []
        for item in v:
            if isinstance(item, str):
                expanded_events.append(Event(name=item))
            elif isinstance(item, dict):
                expanded_events.append(Event.model_validate(item))
            else:
                raise ValueError(f"Invalid event definition: {item}. Must be either a string or a dictionary.")
        return expanded_events

    @field_validator("errors", mode="before")
    def expand_short_form_errors(cls, v: list[dict | str]) -> list[Error]:
        expanded_errors = []
        for item in v:
            if isinstance(item, str):
                expanded_errors.append(Error(name=item))
            elif isinstance(item, dict):
                expanded_errors.append(Error.model_validate(item))
            else:
                raise ValueError(f"Invalid error definition: {item}. Must be either a string or a dictionary.")
        return expanded_errors

    # @model_validator(mode="after")
    # def validate_state_name_uniqueness(self) -> Self:
    #     name_counts = Counter([s.name for s in self.states])
    #     if any(v > 1 for v in name_counts.values()):
    #         counted_strs = [f"{symbol} ({symbol_count})" for symbol, symbol_count in name_counts.items()]
    #         multiname_str = ", ".join(counted_strs)
    #         raise ValueError(f"StateMachine<{self.machine}> does not have unique state names. The following names are defined multiple times: {multiname_str}")
    #     return self

    # @model_validator(mode="after")
    # def validate_event_name_uniqueness(self) -> Self:
    #     name_counts = Counter([e.name for e in self.events])
    #     if any(v > 1 for v in name_counts.values()):
    #         counted_strs = [f"{symbol} ({symbol_count})" for symbol, symbol_count in name_counts.items()]
    #         multiname_str = ", ".join(counted_strs)
    #         raise ValueError(f"StateMachine<{self.machine}> does not have unique event names. The following names are defined multiple times: {multiname_str}")
    #     return self

    # @model_validator(mode="after")
    # def validate_error_name_uniqueness(self) -> Self:
    #     name_counts = Counter([e.name for e in self.errors])
    #     if any(v > 1 for v in name_counts.values()):
    #         counted_strs = [f"{symbol} ({symbol_count})" for symbol, symbol_count in name_counts.items()]
    #         multiname_str = ", ".join(counted_strs)
    #         raise ValueError(f"StateMachine<{self.machine}> does not have unique error names. The following names are defined multiple times: {multiname_str}")
    #     return self

    # @model_validator(mode="after")
    # def validate_monotonic_state_ids(self) -> Self:
    #     # Extract IDs
    #     ids = [s.id for s in self.states]
    #     # Case 1: Some IDs missing → assign all fresh IDs
    #     if any(i is None for i in ids):
    #         logging.debug(
    #             "StateMachine<%s>: Some states are missing IDs. Assigning fresh monotonic IDs based on definition order.",
    #             self.machine,
    #         )
    #         for idx, s in enumerate(self.states):
    #             s.id = idx
    #             logging.debug("StateMachine<%s>: Auto-assigned ID %s to state '%s'.", self.machine, s.id, s.name)
    #         return self
    #     # Case 2: All IDs present → validate monotonicity
    #     sorted_ids = sorted(ids)
    #     expected = list(range(len(ids)))
    #     if sorted_ids != expected:
    #         raise ValueError(f"StateMachine<{self.machine}>: State IDs must be monotonic and contiguous starting at 0. Found {ids}, expected {expected}.")
    #     return self

    # @model_validator(mode="after")
    # def validate_monotonic_event_ids(self) -> Self:
    #     # Extract IDs
    #     ids = [e.id for e in self.events]
    #     # Case 1: Some IDs missing → assign all fresh IDs
    #     if any(i is None for i in ids):
    #         logging.debug(
    #             "StateMachine<%s>: Some events are missing IDs. Assigning fresh monotonic IDs based on definition order.",
    #             self.machine,
    #         )
    #         for idx, e in enumerate(self.events):
    #             e.id = idx
    #             logging.debug("StateMachine<%s>: Auto-assigned ID %s to event '%s'.", self.machine, e.id, e.name)
    #         return self
    #     # Case 2: All IDs present → validate monotonicity
    #     sorted_ids = sorted(ids)
    #     expected = list(range(len(ids)))
    #     if sorted_ids != expected:
    #         raise ValueError(f"StateMachine<{self.machine}>: Event IDs must be monotonic and contiguous starting at 0. Found {ids}, expected {expected}.")
    #     return self

    # @model_validator(mode="after")
    # def validate_monotonic_error_ids(self) -> Self:
    #     # Extract IDs
    #     ids = [e.id for e in self.errors]
    #     # Case 1: Some IDs missing → assign all fresh IDs
    #     if any(i is None for i in ids):
    #         logging.debug(
    #             "StateMachine<%s>: Some errors are missing IDs. Assigning fresh monotonic IDs based on definition order.",
    #             self.machine,
    #         )
    #         for idx, e in enumerate(self.errors):
    #             e.id = idx
    #             logging.debug("StateMachine<%s>: Auto-assigned ID %s to error '%s'.", self.machine, e.id, e.name)
    #         return self
    #     # Case 2: All IDs present → validate monotonicity
    #     sorted_ids = sorted(ids)
    #     expected = list(range(len(ids)))
    #     if sorted_ids != expected:
    #         raise ValueError(f"StateMachine<{self.machine}>: Error IDs must be monotonic and contiguous starting at 0. Found {ids}, expected {expected}.")
    #     return self

    # @model_validator(mode="after")
    # def validate_transition_reference_existence(self) -> Self:
    #     # Build lookup tables
    #     state_map = self._flatten_states(self.states)
    #     evt_map: dict[str, Event] = {e.name: e for e in self.events}
    #     # Validate that all references exist
    #     for t in self.transitions:
    #         # Validate source state
    #         if t.src_state not in state_map:
    #             raise ValueError(f"Transition {t} references unknown source state '{t.src_state}'. Valid states: {', '.join(state_map.keys())}")
    #         # Validate target state
    #         if t.tgt_state not in state_map:
    #             raise ValueError(f"Transition {t} references unknown target state '{t.tgt_state}'. Valid states: {', '.join(state_map.keys())}")
    #         # Validate trigger event
    #         if t.evt not in evt_map:
    #             raise ValueError(f"Transition {t} references unknown event '{t.evt}'. Valid events: {', '.join(evt_map.keys())}")
    #         # Validate target entry event
    #         if t.tgt_entry_evt is not None and t.tgt_entry_evt not in evt_map:
    #             raise ValueError(f"Transition {t} references unknown target entry event '{t.tgt_entry_evt}'. Valid events: {', '.join(evt_map.keys())}")
    #     return self

    # @model_validator(mode="after")
    # def validate_transition_pseudostate_legality(self) -> Self:
    #     for t in self.transitions:
    #         src = self.get_state(t.src_state)
    #         tgt = self.get_state(t.tgt_state)
    #         # Cannot transition into a non-composite initial pseudostate
    #         if tgt.type == StateType.INITIAL and not tgt.is_substate:
    #             raise IllegalTransitionError("Cannot transition into a non-composite initial state.", t, self.machine)
    #         # Cannot transition out of a final or terminal pseudostate
    #         if src.type in {StateType.FINAL, StateType.TERMINAL}:
    #             raise IllegalTransitionError("Cannot transition out of a Final or Terminal pseudostate.", t, self.machine)
    #     return self

    # @model_validator(mode="after")
    # def validate_pseudostate_semantics(self) -> Self:
    #     flattened_states = self._flatten_states(self.states)
    #     for s in flattened_states.values():
    #         # Entry/Exit pseudostates must be inside composite states
    #         if s.type in {StateType.ENTRY, StateType.EXIT} and not s.is_substate:
    #             raise IllegalStateError("Entry / Exit pseudostates must be children of composite states.", s, self.machine)
    #         incoming_transitions = self.get_incoming_transitions(s)
    #         num_incoming_transitions = len(incoming_transitions)
    #         outgoing_transitions = self.get_outgoing_transitions(s)
    #         num_outgoing_transitions = len(outgoing_transitions)
    #         # Choice/Junction pseudostate must have >= 2 outgoing transitions
    #         if s.type in {StateType.CHOICE, StateType.JUNCTION} and num_incoming_transitions < 2:
    #             raise IllegalStateError("Choice / Junction pseudostates must have >=2 outgoing transitions.", s, self.machine)
    #         # Join pseudostate must have >= 2 incoming transitions and 1 outgoing transition
    #         if s.type == StateType.JOIN:
    #             if num_incoming_transitions < 2:
    #                 raise IllegalStateError("Join pseudostates must have >= 2 incoming transitions.", s, self.machine)
    #             if num_outgoing_transitions != 1:
    #                 raise IllegalStateError("Join pseudostates must have exactly 1 outgoing transition.", s, self.machine)
    #         # Fork pseudostate must have >= 2 outgoing transitions and 1 incoming transition
    #         if s.type == StateType.FORK:
    #             if num_incoming_transitions != 1:
    #                 raise IllegalStateError("Fork pseudostates must have exactly 1 incoming transition.", s, self.machine)
    #             if num_outgoing_transitions < 2:
    #                 raise IllegalStateError("Fork pseudostates must have >= 2 outgoing transitions.", s, self.machine)
    #     return self

    # @model_validator(mode="after")
    # def validate_hierarchy_semantics(self) -> Self:
    #     # A transition into a composite state must target its default/initial substate
    #     # A transition out of a composite state must originate from its leaf (simple) substate
    #     for t in self.transitions:
    #         src = self.get_state(t.src_state)
    #         tgt = self.get_state(t.tgt_state)
    #         # No transitions may target a composite state directly unless explicitly allowed by SMAL
    #         if tgt.type == StateType.COMPOSITE:
    #             raise IllegalTransitionError("Transitions cannot directly target a composite state.", t, self.machine)
    #         # No transitions may originate from a composite state unless explicitly allowed by SMAL
    #         if src.type == StateType.COMPOSITE:
    #             raise IllegalTransitionError("Transitions cannot originate from a composite state.", t, self.machine)
    #     return self

    # @model_validator(mode="after")
    # def validate_entry_event_semantics(self) -> Self:
    #     # Target state entry event must be valid for the target state
    #     # Composite states may forbid entry events
    #     # Pseudostates may forbid entry events
    #     # If target entry event is present, the target must be a simple state
    #     for t in [transition for transition in self.transitions if transition.tgt_entry_evt]:
    #         tgt = self.get_state(t.tgt_state)
    #         if not tgt.type == StateType.SIMPLE:
    #             raise IllegalTransitionError("Target entry events may only target simple states.", t, self.machine)
    #     return self

    # @model_validator(mode="after")
    # def validate_state_reachability(self) -> Self:
    #     # Every state except the root-level initial state must be reachable
    #     # All substates within a composite state must be reachable
    #     # Pseudostates must not be dead ends unless they are Final/Terminal pseudostates
    #     return self

    # @model_validator(mode="after")
    # def validate_no_illegal_cycles(self) -> Self:
    #     # Cycles through pseudostates
    #     # Cycles through Final/Terminal states
    #     # Cycles that violate hierarchy
    #     # Legal loops are allowed
    #     return self

    # @model_validator(mode="after")
    # def validate_transition_determinism(self) -> Self:
    #     # No two transitions from the same state share the same event
    #     # No two transitions from the same pseudostate violate UML semantics
    #     # Choice/Junction pseudostates must be deterministic unless SMAL supports guards
    #     return self

    # @model_validator(mode="after")
    # def validate_completeness(self) -> Self:
    #     # Composite states must have 1 initial substate
    #     return self


SMALFile: TypeAlias = StateMachine
