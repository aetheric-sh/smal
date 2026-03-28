import logging
from collections import Counter
from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self

from smal.schemas.smal_command import SMALCommand
from smal.schemas.smal_enum import SMALEnum
from smal.schemas.smal_error import SMALError
from smal.schemas.smal_event import SMALEvent
from smal.schemas.smal_state import SMALState
from smal.schemas.smal_struct import SMALStruct
from smal.schemas.smal_transition import SMALTransition
from smal.schemas.utilities import IdentifierValidationMixin, SemverValidationMixin
from smal.utilities import constants as SMALConstants


class SMALFile(IdentifierValidationMixin, SemverValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("machine",)
    SEMVER_FIELDS: ClassVar[tuple[str]] = ("version",)

    machine: str = Field(..., description="Name of this state machine.")
    version: str = Field(..., description="Semantic version (major.minor.patch) of this state machine.")
    states: list[SMALState] = Field(..., description="States associated with this state machine.")
    events: list[SMALEvent] = Field(default_factory=list, description="Events associated with this state machine, if any.")
    commands: list[SMALCommand] = Field(default_factory=list, description="Commands associated with this state machine, if any.")
    errors: list[SMALError] = Field(default_factory=list, description="Errors associated with this state machine, if any.")
    constants: dict[str, str | int] = Field(default_factory=dict, description="Constants to define for this state machine, if any.")
    # messages: list[SMALMessage] = Field(default_factory=list, description="Messages associated with this state machine, if any.")
    transitions: list[SMALTransition] = Field(default_factory=list, description="State transitions associated with this state machine, if any.")
    enums: list[SMALEnum] = Field(default_factory=list, description="Enumerations to define for this state machine, if any.")
    structs: list[SMALStruct] = Field(default_factory=list, description="Structures to define for this state machine, if any.")
    debug: SMALStruct | None = Field(default=None, description="Debugging structure associated with this state machine, if any.")
    description: str | None = Field(default=None, description="Description of the state machine.")

    @field_validator("states", mode="before")
    def expand_short_form_states(cls, v: list[dict | str]) -> list[SMALState]:
        expanded_states = []
        for item in v:
            if isinstance(item, str):
                expanded_states.append(SMALState(name=item))
            elif isinstance(item, dict):
                expanded_states.append(SMALState.model_validate(item))
            else:
                raise ValueError(f"Invalid state definition: {item}. Must be either a string or a dictionary.")
        return expanded_states

    @field_validator("events", mode="before")
    def expand_short_form_events(cls, v: list[dict | str]) -> list[SMALEvent]:
        expanded_events = []
        for item in v:
            if isinstance(item, str):
                expanded_events.append(SMALEvent(name=item))
            elif isinstance(item, dict):
                expanded_events.append(SMALEvent.model_validate(item))
            else:
                raise ValueError(f"Invalid event definition: {item}. Must be either a string or a dictionary.")
        return expanded_events

    @field_validator("errors", mode="before")
    def expand_short_form_errors(cls, v: list[dict | str]) -> list[SMALError]:
        expanded_errors = []
        for item in v:
            if isinstance(item, str):
                expanded_errors.append(SMALError(name=item))
            elif isinstance(item, dict):
                expanded_errors.append(SMALError.model_validate(item))
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
            logging.warning("Machine<%s>: Some states are missing IDs. Auto-assigning IDs based on order of definition.", self.machine)
            for s in self.states:
                s.id = self.states.index(s)
                logging.debug("Machine<%s>: Auto-assigned ID %s to state '%s'.", self.machine, s.id, s.name)
        # Validate that all events are properly identified
        evt_ids = {e.id for e in self.events}
        if None in evt_ids:
            logging.warning("Machine<%s>: Some events are missing IDs. Auto-assigning IDs based on order of definition.", self.machine)
            for e in self.events:
                e.id = self.events.index(e)
                logging.debug("Machine<%s>: Auto-assigned ID %s to event '%s'.", self.machine, e.id, e.name)
        # Validate that all errors are properly identified
        err_ids = {e.id for e in self.errors}
        if None in err_ids:
            logging.warning("Machine<%s>: Some errors are missing IDs. Auto-assigning IDs based on order of definition.", self.machine)
            for e in self.errors:
                e.id = self.errors.index(e)
                logging.debug("Machine<%s>: Auto-assigned ID %s to error '%s'.", self.machine, e.id, e.name)
        # Validate that all SMALTransition objects reference existing states, events, etc.
        state_map: dict[str, SMALState] = {s.name: s for s in self.states}
        evt_map: dict[str, SMALEvent] = {e.name: e for e in self.events}
        for transition in self.transitions:
            if transition.trigger_state not in state_map:
                raise ValueError(f"Transition {transition} references unknown trigger state '{transition.trigger_state}'. Must be one of: {', '.join(state_map.keys())}")
            if transition.trigger_evt not in evt_map:
                raise ValueError(f"Transition {transition} references unknown trigger event '{transition.trigger_evt}'. Must be one of: {', '.join(evt_map.keys())}")
            if transition.landing_state not in state_map:
                raise ValueError(f"Transition {transition} references unknown landing state '{transition.landing_state}'. Must be one of: {', '.join(state_map.keys())}")
            if transition.landing_state_entry_evt is not None and transition.landing_state_entry_evt not in evt_map:
                raise ValueError(
                    f"Transition {transition} references unknown landing state entry event '{transition.landing_state_entry_evt}'. Must be one of: {', '.join(evt_map.keys())}"
                )
        return self

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
