from __future__ import annotations  # Until Python 3.14

from typing import TypeAlias

from pydantic import BaseModel, Field, PrivateAttr


class Transition(BaseModel):
    """Schema defining a transition between states in a state machine."""

    src_state: str = Field(..., description="The name of the state the machine must be in in order for evt to trigger this transition.")
    evt: str = Field(..., description="The name of the event that triggers this transition.")
    actions: list[str] = Field(..., description="The sequence of functions to invoke when evt is received while in src_state.")
    tgt_state: str = Field(..., description="The state to transition into after executing actions in response to receiving evt while in src_state.")
    tgt_entry_evt: str | None = Field(default=None, description="Event to trigger upon entering tgt_state, if any.")
    _graphable: bool = PrivateAttr(default=True)

    def __repr__(self) -> str:
        return f"({self.src_state}, {self.evt}, [{', '.join(self.actions)}], {self.tgt_state}, {self.tgt_entry_evt})"

    def __str__(self) -> str:
        return self.__repr__()

    def set_graphable(self, graphable: bool) -> None:
        self._graphable = graphable

    @property
    def graphable(self) -> bool:
        return self._graphable


EphemeralTransition: TypeAlias = Transition


class IllegalTransitionError(ValueError):
    def __init__(self, message: str, transition: Transition | None = None, state_machine_name: str | None = None) -> None:
        details = []
        if transition is not None:
            details.append(f"Transition: {transition}")
            details.append(f"Source state: {transition.src_state}")
            details.append(f"Target state: {transition.tgt_state}")
            details.append(f"Event: {transition.evt}")
            if transition.tgt_entry_evt:
                details.append(f"Target entry event: {transition.tgt_entry_evt}")

        if details:
            message = f"{message}\n" + "\n".join(details)

        if state_machine_name:
            message = f"StateMachine<{state_machine_name}>: {message}"
        super().__init__(message)
