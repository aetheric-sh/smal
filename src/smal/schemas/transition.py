"""Module defining the Transition schema for SMAL state machines."""

from __future__ import annotations  # Until Python 3.14

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from smal.schemas.action import Action  # noqa: TC001 - Pydantic requires this at runtime
from smal.schemas.guard import Guards  # noqa: TC001 - Pydantic requires this at runtime
from smal.utilities.types import Identifier  # noqa: TC001 - Pydantic requires this at runtime


class Transition(BaseModel):
    """Schema representing a transition in a state machine."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    src: Identifier = Field(description="The source state.")
    evt: Identifier | None = Field(
        default=None,
        description="Event that must be received while in src state to trigger this transition. If None, it is a completion transition.",
    )
    guard: Guards = Field(default_factory=list, description="Guard condition(s) for the transition.")  # TODO: Make this a single guard
    is_else: bool = Field(default=False, description="Fires only if no sibling guard(s) match.")
    actions: list[Action] = Field(
        default_factory=list,
        description="The sequence of functions to invoke (in order of definition) when evt is received while in src.",
    )
    tgt: Identifier | None = Field(default=None, description="The state to transition into after executing actions in response to receiving evt while in src.")
    tgt_entry_evt: Identifier | None = Field(default=None, description="Event to fire upon entry of tgt state.")
    _original_src: Identifier | None = PrivateAttr(default=None)
    _original_tgt: Identifier | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _check_local(self) -> Transition:
        if self.is_else and self.guard:
            raise ValueError("'else' transitions cannot also carry a guard predicate.")
        if self.is_completion and self.is_internal:
            raise ValueError("Completion transitions need a target; an internal one would loop forever.")
        if self.is_internal and self.tgt_entry_evt:
            raise ValueError("Internal transitions don't enter a state, so tgt_entry_evt is invalid.")
        return self

    @property
    def is_completion(self) -> bool:
        """Return whether or not this transition is a completion transition, e.g. a transition with no triggering event.

        Completion transitions are executed automatically upon entering its defined src state, assuming its associated guard predicate holds.

        Returns:
            bool: True if this transition is a completion transition, False otherwise.

        """
        return self.evt is None

    @property
    def is_internal(self) -> bool:
        """Return whether or not this transition is an internal transition, e.g. a transition that has a trigger but no target state change.

        Internal transitions are useful for allowing a state to react to something without disturbing itself.

        Returns:
            bool: True if this transition is internal, False otherwise.

        """
        return self.tgt is None

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


class ShorthandTransition(BaseModel):
    """Model defining the shorthand syntax for specifying transitions in a state machine. This allows users to define transitions in a more concise way."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,  # So class can be instantiated with real variable names OR aliases
        extra="ignore",
        frozen=True,
    )
    tgt: Identifier = Field(..., alias="target", description="The state to transition into after executing actions in response to receiving evt while in src.")
    guard: Guards = Field(default_factory=list, description="Guard condition(s) for the transition.")
    actions: list[Identifier] = Field(
        default_factory=list,
        description="The sequence of functions to invoke (in order of definition) when evt is received while in src.",
    )
    tgt_entry_evt: Identifier | None = Field(default=None, alias="on_entry", description="Event to trigger upon entering tgt, if any.")


class ShorthandTransitionMap(BaseModel):
    """Model defining the shorthand syntax for specifying a map of transitions in a state machine.

    This allows users to define transitions in a more concise way.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)

    transitions: dict[str, dict[Identifier, Identifier | ShorthandTransition]]

    def to_transitions(self) -> list[Transition]:
        """Convert this TransitionMapShorthand into a list of full Transition objects.

        Returns:
            list[Transition]: The list of Transition objects represented by this TransitionMapShorthand.

        """
        out: list[Transition] = []
        for src, evt_map in self.transitions.items():
            for evt, sh_t in evt_map.items():
                if isinstance(sh_t, str):
                    # The transition is defined simply as a target state identifier
                    out.append(Transition(src=src, evt=evt, tgt=sh_t))
                else:
                    # The transition is defined with a shorthand object
                    out.append(
                        Transition(
                            src=src,
                            evt=evt,
                            guard=sh_t.guard,
                            actions=sh_t.actions,
                            tgt=sh_t.tgt,
                            tgt_entry_evt=sh_t.tgt_entry_evt,
                        ),
                    )
        return out


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
