from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from smal.schemas.smal_command import SMALCommand
from smal.schemas.smal_enum import SMALEnum
from smal.schemas.smal_error import SMALError
from smal.schemas.smal_event import SMALEvent
from smal.schemas.smal_state import SMALState

# from smal.schemas.smal_message import SMALMessage
from smal.schemas.smal_struct import SMALStruct
from smal.schemas.smal_transition import SMALTransition
from smal.schemas.utilities import IdentifierValidationMixin, SemverValidationMixin


class SMALFile(IdentifierValidationMixin, SemverValidationMixin, BaseModel):
    IDENTIFIER_FIELDS: ClassVar[tuple[str]] = ("machine",)
    SEMVER_FIELDS: ClassVar[tuple[str]] = ("version",)
    SUPPORTED_FILE_EXTENSIONS: ClassVar[set[str]] = {".smal", ".yaml", ".yml"}

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

    @model_validator(mode="after")
    def validate_smal_file(self) -> Self:
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
        if not path.suffix or path.suffix not in self.SUPPORTED_FILE_EXTENSIONS:
            raise ValueError(f"SMAL file must have one of the following extensions: {', '.join(self.SUPPORTED_FILE_EXTENSIONS)}")
        model_data = self.model_dump(exclude_unset=exclude_unset, exclude_defaults=exclude_defaults, exclude_none=exclude_none, exclude_computed_fields=exclude_computed_fields)
        yaml_data = yaml.safe_dump(model_data, sort_keys=sort_keys, indent=indent)
        path.write_text(yaml_data, encoding="utf-8")

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        path = Path(path)
        if not path.suffix or path.suffix not in cls.SUPPORTED_FILE_EXTENSIONS:
            raise ValueError(f"SMAL file must have one of the following extensions: {', '.join(cls.SUPPORTED_FILE_EXTENSIONS)}")
        yaml_data = path.read_text(encoding="utf-8")
        model_data = yaml.safe_load(yaml_data)
        model = cls.model_validate(model_data)
        return model
