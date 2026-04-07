"""Module defining the Transition schema for SMAL state machines."""

from __future__ import annotations  # Until Python 3.14

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class TransitionSpecShorthand(BaseModel):
    """Model defining the shorthand syntax for specifying transitions in a state machine. This allows users to define transitions in a more concise way."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,  # So class can be instantiated with real variable names OR aliases
    )
    tgt: str = Field(..., alias="target", description="The state to transition into after executing actions in response to receiving evt while in src.")
    actions: list[str] = Field(default_factory=list, description="The sequence of functions to invoke when evt is received while in src.")
    tgt_entry_evt: str | None = Field(default=None, alias="on_entry", description="Event to trigger upon entering tgt, if any.")


class TransitionMapShorthand(BaseModel):
    """Model defining the shorthand syntax for specifying a map of transitions in a state machine. This allows users to define transitions in a more concise way."""

    transitions: dict[str, dict[str, str | TransitionSpecShorthand]]

    def to_transitions(self) -> list[Transition]:
        """Convert this TransitionMapShorthand into a list of full Transition objects.

        Returns:
            list[Transition]: The list of Transition objects represented by this TransitionMapShorthand.

        """
        out: list[Transition] = []
        for src, evt_map in self.transitions.items():
            for evt, spec in evt_map.items():
                if isinstance(spec, str):
                    out.append(
                        Transition(
                            src=src,
                            evt=evt,
                            actions=[],
                            tgt=spec,
                            tgt_entry_evt=None,
                        ),
                    )
                else:
                    out.append(
                        Transition(
                            src=src,
                            evt=evt,
                            actions=spec.actions,
                            tgt=spec.tgt,
                            tgt_entry_evt=spec.tgt_entry_evt,
                        ),
                    )
        return out


class Transition(BaseModel):
    """Schema defining a transition between states in a state machine."""

    src: str = Field(..., description="The name of the state the machine must be in in order for evt to trigger this transition.")
    evt: str = Field(..., description="The name of the event that triggers this transition.")
    actions: list[str] = Field(..., description="The sequence of functions to invoke when evt is received while in src.")
    tgt: str = Field(..., description="The state to transition into after executing actions in response to receiving evt while in src.")
    tgt_entry_evt: str | None = Field(default=None, description="Event to trigger upon entering tgt, if any.")
    _original_src: str | None = PrivateAttr(default=None)
    _original_tgt: str | None = PrivateAttr(default=None)

    def __repr__(self) -> str:
        """Get the string representing this object when it is printed.

        Returns:
            str: The string representation of this object.

        """
        return f"({self.src}, {self.evt}, [{', '.join(self.actions)}], {self.tgt}, {self.tgt_entry_evt})"

    def __str__(self) -> str:
        """Get the string representing this object when it is cast to a str.

        Returns:
            str: The string representation of this object.

        """
        return self.__repr__()

    @property
    def original_src(self) -> str | None:
        """Get the original src state of this transition.

        Returns:
            str | None: The original src state of this transition, or None if it has not been modified.

        """
        return self._original_src

    @property
    def original_tgt(self) -> str | None:
        """Get the original tgt state of this transition.

        Returns:
            str | None: The original tgt state of this transition, or None if it has not been modified.

        """
        return self._original_tgt

    def set_original_src(self, original_src: str) -> None:
        """Set the original src state of this transition.

        Args:
            original_src (str): The original src state of this transition before it was modified during validation.

        """
        self._original_src = original_src

    def set_original_tgt(self, original_tgt: str) -> None:
        """Set the original tgt state of this transition.

        Args:
            original_tgt (str): The original tgt state of this transition before it was modified during validation.

        """
        self._original_tgt = original_tgt

    @classmethod
    def from_shorthand(cls, data: Any) -> Transition:
        pass


class IllegalTransitionError(ValueError):
    """Exception raised when a transition violates SMAL rules, such as targeting an invalid state type."""

    def __init__(self, message: str, transition: Transition | None = None, state_machine_name: str | None = None) -> None:
        """Initialize the IllegalTransitionError.

        Args:
            message (str): The error message describing the nature of the illegal transition.
            transition (Transition | None, optional): The transition that caused the error. Defaults to None.
            state_machine_name (str | None, optional): The name of the state machine where the error occurred. Defaults to None.

        """
        details = []
        if transition is not None:
            details.append(f"Transition: {transition}")
            details.append(f"Source state: {transition.src}")
            details.append(f"Target state: {transition.tgt}")
            details.append(f"Event: {transition.evt}")
            if transition.tgt_entry_evt:
                details.append(f"Target entry event: {transition.tgt_entry_evt}")

        if details:
            message = f"{message}\n" + "\n".join(details)

        if state_machine_name:
            message = f"StateMachine<{state_machine_name}>: {message}"
        super().__init__(message)
