from __future__ import annotations  # Until Python 3.14

import logging
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, ClassVar, TypeAlias

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator
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

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,  # So class can be instantiated with real variable names or aliases
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

    def get_ordered_flat_global_state_list(self) -> list[State]:
        # Recursive helper to flatten the states
        def helper() -> list[State]:
            ordered: list[State] = []

            def walk(state: State):
                ordered.append(state)
                for sub in sorted(state.substates, key=lambda s: s.id or 0):
                    walk(sub)

            # Walk all top-level states in sorted order
            for state in sorted(self.states, key=lambda s: s.id or 0):
                walk(state)
            return ordered

        # Deepcopy so we don't alter the originals
        states = deepcopy(helper())
        # Ensure all states are now monotonically increasing id
        for i, state in enumerate(states):
            state.id = i
        # Done
        return states

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


SMALFile: TypeAlias = StateMachine
