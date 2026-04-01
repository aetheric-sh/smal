"""Module defining validation rules for state machines."""

from __future__ import annotations  # Until Python 3.14

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from smal.schemas.state import EphemeralState, StateType
from smal.schemas.transition import EphemeralTransition

if TYPE_CHECKING:
    from smal.schemas import StateMachine


class CorrectionLike(Protocol):
    """Protocol defining the structure for an encapsulated correction for a SMAL state machine."""

    description: str
    enabled: bool
    group: str | None

    @property
    def name(self) -> str:
        """The name of this CorrectionLike."""

    def pre_application(self, machine: StateMachine) -> None:
        """Handle any processing that needs to be done before applying this correction.

        Args:
            machine (StateMachine): The state machine the correction is being applied to.

        """

    def apply(self, machine: StateMachine) -> None:
        """Apply this correction to the given state machine.

        Args:
            machine (StateMachine): The state machine the correction is being applied to.

        """

    def post_application(self, machine: StateMachine) -> None:
        """Handle any post-processing that needs to be done after applying this correction.

        Args:
            machine (StateMachine): The state machine the correction is being applied to.

        """


@dataclass(frozen=True)
class Correction(CorrectionLike):
    """Base class for all CorrectionLike objects."""

    description: str = ""
    enabled: bool = True
    group: str | None = None

    @property
    def name(self) -> str:
        """Return the name of this Correction.

        Returns:
            str: The name of this correction.

        """
        parts = re.split(r"(?<=[a-z])(?=[A-Z])", self.__class__.__name__)
        return "-".join([p.lower() for p in parts])

    def pre_application(self, machine: StateMachine) -> None:
        """Handle any processing that needs to be done before applying this correction.

        Args:
            machine (StateMachine): The state machine the correction is being applied to.

        """
        # NOTE: Not raising exception here, as this is an optional method

    def apply(self, machine: StateMachine) -> None:
        """Apply this correction to the given state machine.

        Args:
            machine (StateMachine): The state machine the correction is being applied to.

        """
        raise NotImplementedError("Correction.apply is a required method and must be implemented by child classes of Correction.")

    def post_application(self, machine: StateMachine) -> None:
        """Handle any post-processing that needs to be done after applying this correction.

        Args:
            machine (StateMachine): The state machine the correction is being applied to.

        """
        # NOTE: Not raising exception here, as this is an optional method


@dataclass(frozen=True)
class InjectRootEphemeralInitialState(Correction):
    """Correction that takes the root-level state marked as initial, and creates an ephemeral initial state that transitions into the root-level state to preserve the label."""

    description: str = "Takes the root-level state marked as initial, and creates an ephemeral initial state that transitions into the root-level state to preserve the label."

    def apply(self, machine: StateMachine) -> None:
        """Apply this correction.

        Args:
            machine (StateMachine): The state machine the correction is being applied to.

        """
        root_initial_states = [s for s in machine.states if s.type == StateType.INITIAL]
        if len(root_initial_states) != 1:
            raise RuntimeError
        root_init = root_initial_states[0]
        ephemeral_init = EphemeralState(f"__eph_initial_{root_init.name}", root_init, morphed_type=StateType.SIMPLE)
        machine.add_ephemeral_state(ephemeral_init)
        eph_init_to_root_init = EphemeralTransition(src_state=ephemeral_init.name, evt="init", actions=[], tgt_state=root_init.name, tgt_entry_evt=None)
        machine.add_ephemeral_transition(eph_init_to_root_init)


@dataclass(frozen=True)
class RedirectCompositeTargetStateTransitions(Correction):
    """Correction that redirects all transitions that would target a composite state directly to instead target that composite state's internal initial substate."""

    description: str = "Redirects all transitions that would target a composite state directly to instead target that composite state's internal initial substate."

    def apply(self, machine: StateMachine) -> None:
        """Apply this correction.

        Args:
            machine (StateMachine): The state machine the correction is being applied to.

        """
        composite_state_map = {s.name: s for s in machine.composite_states}
        for t in machine.transitions:
            if t.tgt_state in composite_state_map:
                composite_state = composite_state_map[t.tgt_state]
                initial_substate = composite_state.initial_substate
                logging.warning(
                    "CORRECTION: Detected transition directly targeting composite state '%s'. Redirecting to internal initial substate '%s'...",
                    t.tgt_state,
                    initial_substate.name,
                )
                # Create ephemeral initial state
                logging.debug(
                    "Adding ephemeral initial state within composite state '%s'",
                    t.tgt_state,
                )
                ephemeral_initial_state = EphemeralState(f"__eph_initial_{t.tgt_state}__", initial_substate, morphed_type=StateType.SIMPLE)
                machine.add_ephemeral_state(ephemeral_initial_state)
                # Create 2 ephemeral transitions:
                # 1. from original source to ephemeral initial state
                logging.debug(
                    "Adding ephemeral transition from state '%s' to ephemeral initial state",
                    t.src_state,
                )
                osrc_to_eph_init = EphemeralTransition(src_state=t.src_state, evt=t.evt, actions=t.actions, tgt_state=ephemeral_initial_state.name, tgt_entry_evt=t.tgt_entry_evt)
                machine.add_ephemeral_transition(osrc_to_eph_init)
                # 2. from ephemeral initial state to composite initial state
                logging.debug(
                    "Adding ephemeral transition from ephemeral initial state to composite initial state '%s'",
                    initial_substate.name,
                )
                eph_init_to_comp_init = EphemeralTransition(
                    src_state=ephemeral_initial_state.name,
                    evt=t.evt,
                    actions=t.actions,
                    tgt_state=initial_substate.name,
                    tgt_entry_evt=t.tgt_entry_evt,
                )
                machine.add_ephemeral_transition(eph_init_to_comp_init)
                # Set the real transition as not graphable
                logging.debug("Marking original transition %s as not graphable to hide it from diagram", t)
                t.set_graphable(False)


ALL_CORRECTIONS: list[CorrectionLike] = [
    InjectRootEphemeralInitialState(),
    RedirectCompositeTargetStateTransitions(),
]
