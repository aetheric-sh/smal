from __future__ import annotations  # Until Python 3.14

import logging
from collections import Counter
from pathlib import Path
from typing import Any, ClassVar

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self, TypeAlias

from smal.schemas.command import Command
from smal.schemas.enumeration import Enumeration
from smal.schemas.error import Error
from smal.schemas.event import Event
from smal.schemas.state import State
from smal.schemas.struct import Struct
from smal.schemas.transition import Transition
from smal.schemas.utilities import IdentifierValidationMixin, SemverValidationMixin
from smal.utilities import constants as SMALConstants


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

    @model_validator(mode="after")
    def validate_smal_file(self) -> Self:
        # Ensure all states are uniquely named
        names = [s.name for s in self.states]
        duplicate_names = [name for name, count in Counter(names).items() if count > 1]
        if duplicate_names:
            raise ValueError(f"Duplicate state names found: {', '.join(duplicate_names)}. All state names must be unique.")
        # Validate that all states are properly identified
        state_ids = {s.id for s in self.states}
        if None in state_ids:
            logging.debug("Machine<%s>: Some states are missing IDs. Auto-assigning IDs based on order of definition.", self.machine)
            for s in self.states:
                s.id = self.states.index(s)
                logging.debug("Machine<%s>: Auto-assigned ID %s to state '%s'.", self.machine, s.id, s.name)
        # Validate that all events are properly identified
        evt_ids = {e.id for e in self.events}
        if None in evt_ids:
            logging.debug("Machine<%s>: Some events are missing IDs. Auto-assigning IDs based on order of definition.", self.machine)
            for e in self.events:
                e.id = self.events.index(e)
                logging.debug("Machine<%s>: Auto-assigned ID %s to event '%s'.", self.machine, e.id, e.name)
        # Validate that all errors are properly identified
        err_ids = {e.id for e in self.errors}
        if None in err_ids:
            logging.debug("Machine<%s>: Some errors are missing IDs. Auto-assigning IDs based on order of definition.", self.machine)
            for e in self.errors:
                e.id = self.errors.index(e)
                logging.debug("Machine<%s>: Auto-assigned ID %s to error '%s'.", self.machine, e.id, e.name)
        # Validate that all SMALTransition objects reference existing states, events, etc.
        state_map = self._flatten_states(self.states)
        evt_map: dict[str, Event] = {e.name: e for e in self.events}
        for transition in self.transitions:
            if transition.src_state not in state_map:
                raise ValueError(f"Transition {transition} references unknown trigger state '{transition.src_state}'. Must be one of: {', '.join(state_map.keys())}")
            if transition.tgt_state not in state_map:
                raise ValueError(f"Transition {transition} references unknown landing state '{transition.tgt_state}'. Must be one of: {', '.join(state_map.keys())}")
            if transition.evt not in evt_map:
                raise ValueError(f"Transition {transition} references unknown trigger event '{transition.evt}'. Must be one of: {', '.join(evt_map.keys())}")
            if transition.tgt_entry_evt and transition.tgt_entry_evt not in evt_map:
                raise ValueError(f"Transition {transition} references unknown landing state entry event '{transition.tgt_entry_evt}'. Must be one of: {', '.join(evt_map.keys())}")
        return self

    @staticmethod
    def _flatten_states(states: list[State], prefix: str = "") -> dict[str, State]:
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

    def get_state(self, name: str) -> State:
        return next(s for s in self.states if s.name == name)


SMALFile: TypeAlias = StateMachine
