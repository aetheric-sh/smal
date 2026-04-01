"""Module defining validation rules for state machines."""

from __future__ import annotations  # Until Python 3.14

import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from smal.schemas.state import IllegalStateError, StateType
from smal.schemas.transition import IllegalTransitionError

if TYPE_CHECKING:
    from smal.schemas.event import Event
    from smal.schemas.state_machine import StateMachine


class RuleLike(Protocol):
    """Protocol defining the structure for an encapsulated validation rule for a SMAL state machine."""

    description: str
    enabled: bool
    group: str | None

    @property
    def name(self) -> str:
        """The name of this RuleLike."""

    def pre_evaluation(self, machine: StateMachine) -> None:
        """Handle any processing that needs to be done before evaluation of this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        """

    def evaluate(self, machine: StateMachine) -> None:
        """Evaluate this rule against the given state machine.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        """

    def post_evaluation(self, machine: StateMachine) -> None:
        """Handle any post-processing that needs to be done after evaluation of this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        """


@dataclass(frozen=True)
class Rule(RuleLike):
    """Base class for all RuleLike objects."""

    description: str = ""
    enabled: bool = True
    group: str | None = None

    @property
    def name(self) -> str:
        """Return the name of this Rule.

        Returns:
            str: The name of this rule.

        """
        parts = re.split(r"(?<=[a-z])(?=[A-Z])", self.__class__.__name__)
        return "-".join([p.lower() for p in parts])

    def pre_evaluation(self, machine: StateMachine) -> None:
        """Handle any processing that needs to be done before evaluation of this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        """
        # NOTE: Not raising exception here, as this is an optional method

    def evaluate(self, machine: StateMachine) -> None:
        """Evaluate this rule against the given state machine.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        """
        raise NotImplementedError("Rule.evaluate is a required method and must be implemented by child classes of Rule.")

    def post_evaluation(self, machine: StateMachine) -> None:
        """Handle any post-processing that needs to be done after evaluation of this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        """
        # NOTE: Not raising exception here, as this is an optional method


@dataclass(frozen=True)
class StateNamesMustBeUnique(Rule):
    """Rule enforcing that all state/substate names must be globally unique."""

    description: str = "All state/substate names must be globally unique with no duplicates."

    def evaluate(self, machine: StateMachine) -> None:
        """Evaluate this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            ValueError: If the state machine violates this rule.

        """
        flattened_states = machine.get_flattened_states()
        name_counts = Counter(list(flattened_states))
        if any(v > 1 for v in name_counts.values()):
            counted_strs = [f"{symbol} ({symbol_count})" for symbol, symbol_count in name_counts.items()]
            multiname_str = ", ".join(counted_strs)
            raise ValueError(f"StateMachine<{machine.name}> does not have unique state/substate names. The following names are defined multiple times: {multiname_str}")


@dataclass(frozen=True)
class EventNamesMustBeUnique(Rule):
    """Rule enforcing that all event names must be globally unique."""

    description: str = "All event names must be globally unique with no duplicates."

    def evaluate(self, machine: StateMachine) -> None:
        """Evaluate this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            ValueError: If the state machine violates this rule.

        """
        name_counts = Counter([e.name for e in machine.events])
        if any(v > 1 for v in name_counts.values()):
            counted_strs = [f"{symbol} ({symbol_count})" for symbol, symbol_count in name_counts.items()]
            multiname_str = ", ".join(counted_strs)
            raise ValueError(f"StateMachine<{machine.name}> does not have unique event names. The following names are defined multiple times: {multiname_str}")


@dataclass(frozen=True)
class ErrorNamesMustBeUnique(Rule):
    """Rule enforcing that all error names must be globally unique."""

    description: str = "All error names must be globally unique with no duplicates."

    def evaluate(self, machine: StateMachine) -> None:
        """Evaluate this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            ValueError: If the state machine violates this rule.

        """
        name_counts = Counter([e.name for e in machine.errors])
        if any(v > 1 for v in name_counts.values()):
            counted_strs = [f"{symbol} ({symbol_count})" for symbol, symbol_count in name_counts.items()]
            multiname_str = ", ".join(counted_strs)
            raise ValueError(f"StateMachine<{machine.name}> does not have unique error names. The following names are defined multiple times: {multiname_str}")


@dataclass(frozen=True)
class StateIDSMustBeMonotonic(Rule):
    """Rule enforcing that all state IDs must be monotonically increasing, starting from 0."""

    description: str = "All state IDs must monotonically increase, starting from 0."

    def evaluate(self, machine: StateMachine) -> None:
        """Evaluate this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            ValueError: If the state machine violates this rule.

        """
        # Extract IDs
        ids = [s.id for s in machine.states]
        # Case 1: Some IDs missing → assign all fresh IDs
        if None in ids:
            logging.debug(
                "StateMachine<%s>: Some states are missing IDs. Assigning fresh monotonic IDs based on definition order.",
                machine.name,
            )
            for idx, s in enumerate(machine.states):
                s.id = idx
                logging.debug("StateMachine<%s>: Auto-assigned ID %s to state '%s'.", machine.name, s.id, s.name)
        # Case 2: All IDs present → validate monotonicity
        sorted_ids = sorted([s.id for s in machine.states])
        expected = list(range(len(ids)))
        if sorted_ids != expected:
            raise ValueError(f"StateMachine<{machine.name}>: State IDs must be monotonic and contiguous starting at 0. Found {ids}, expected {expected}.")


@dataclass(frozen=True)
class EventIDSMustBeMonotonic(Rule):
    """Rule enforcing that all event IDs must be monotonically increasing, starting from 0."""

    description: str = "All event IDs must monotonically increase, starting from 0."

    def evaluate(self, machine: StateMachine) -> None:
        """Evaluate this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            ValueError: If the state machine violates this rule.

        """
        # Extract IDs
        ids = [e.id for e in machine.events]
        # Case 1: Some IDs missing → assign all fresh IDs
        if None in ids:
            logging.debug(
                "StateMachine<%s>: Some events are missing IDs. Assigning fresh monotonic IDs based on definition order.",
                machine.name,
            )
            for idx, e in enumerate(machine.events):
                e.id = idx
                logging.debug("StateMachine<%s>: Auto-assigned ID %s to event '%s'.", machine.name, e.id, e.name)
        # Case 2: All IDs present → validate monotonicity
        sorted_ids = sorted([e.id for e in machine.events])
        expected = list(range(len(ids)))
        if sorted_ids != expected:
            raise ValueError(f"StateMachine<{machine.name}>: Event IDs must be monotonic and contiguous starting at 0. Found {ids}, expected {expected}.")


@dataclass(frozen=True)
class ErrorIDSMustBeMonotonic(Rule):
    """Rule enforcing that all error IDs must be monotonically increasing, starting from 0."""

    description: str = "All error IDs must monotonically increase, starting from 0."

    def evaluate(self, machine: StateMachine) -> None:
        """Evaluate this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            ValueError: If the state machine violates this rule.

        """
        # Extract IDs
        ids = [e.id for e in machine.errors]
        # Case 1: Some IDs missing → assign all fresh IDs
        if None in ids:
            logging.debug(
                "StateMachine<%s>: Some errors are missing IDs. Assigning fresh monotonic IDs based on definition order.",
                machine.name,
            )
            for idx, e in enumerate(machine.errors):
                e.id = idx
                logging.debug("StateMachine<%s>: Auto-assigned ID %s to error '%s'.", machine.name, e.id, e.name)
        # Case 2: All IDs present → validate monotonicity
        sorted_ids = sorted([e.id for e in machine.errors])
        expected = list(range(len(ids)))
        if sorted_ids != expected:
            raise ValueError(f"StateMachine<{machine.name}>: Error IDs must be monotonic and contiguous starting at 0. Found {ids}, expected {expected}.")


@dataclass(frozen=True)
class NoTransitionIntoSimpleInitial(Rule):
    """Rule enforcing that transitions into simple initial pseudostates are illegal."""

    description: str = "Transitions cannot be made into a non-composite initial pseudostate."
    enabled: bool = False  # TODO: Enable this later

    def evaluate(self, machine: StateMachine) -> None:
        """Evalute this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            IllegalTransitionError: If the state machine violates this rule.

        """
        for t in machine.transitions:
            tgt = machine.get_state(t.tgt_state)
            if tgt.type == StateType.INITIAL and not tgt.is_substate:
                raise IllegalTransitionError(self.description, t, machine.name)


@dataclass(frozen=True)
class TransitionsMustReferenceExistingSymbols(Rule):
    """Rule enforcing that all transitions must reference existing symbols in the state machine."""

    description: str = "All transitions must reference existing symbols from the state machine."

    def evaluate(self, machine: StateMachine) -> None:
        """Evalute this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            ValueError: If the state machine violates this rule.

        """
        # Build lookup tables
        state_map = machine.get_flattened_states()
        evt_map: dict[str, Event] = {e.name: e for e in machine.events}
        # Validate that all references exist
        for t in machine.transitions:
            # Validate source state
            if t.src_state not in state_map:
                raise ValueError(f"Transition {t} references unknown source state '{t.src_state}'. Valid states: {', '.join(state_map.keys())}")
            # Validate target state
            if t.tgt_state not in state_map:
                raise ValueError(f"Transition {t} references unknown target state '{t.tgt_state}'. Valid states: {', '.join(state_map.keys())}")
            # Validate trigger event
            if t.evt not in evt_map:
                raise ValueError(f"Transition {t} references unknown event '{t.evt}'. Valid events: {', '.join(evt_map.keys())}")
            # Validate target entry event
            if t.tgt_entry_evt is not None and t.tgt_entry_evt not in evt_map:
                raise ValueError(f"Transition {t} references unknown target entry event '{t.tgt_entry_evt}'. Valid events: {', '.join(evt_map.keys())}")


@dataclass(frozen=True)
class NoTransitionOutOfFinalOrTerminal(Rule):
    """Rule enforcing that transitions out of the Final or Terminal pseudostates are illegal."""

    description: str = "Transitions cannot be made out of the Final or Terminal pseudostates."

    def evaluate(self, machine: StateMachine) -> None:
        """Evalute this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            IllegalTransitionError: If the state machine violates this rule.

        """
        # Validate that all references exist
        for t in machine.transitions:
            src = machine.get_state(t.src_state)
            if src.type in {StateType.FINAL, StateType.TERMINAL}:
                raise IllegalTransitionError("Cannot transition out of a Final or Terminal pseudostate.", t, machine.name)


@dataclass(frozen=True)
class EntryExitStatesRequireParent(Rule):
    """Rule enforcing that Entry/Exit pseudostates are required to live within a Composite state."""

    description: str = "All Entry/Exit pseudostates are required to have a parent Composite state."

    def evaluate(self, machine: StateMachine) -> None:
        """Evalute this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            IllegalStateError: If the state machine violates this rule.

        """
        flattened = machine.get_flattened_states()
        for s in flattened.values():
            if s.type in {StateType.ENTRY, StateType.EXIT} and not s.is_substate:
                raise IllegalStateError("Entry / Exit pseudostates must be children of composite states.", s, machine.name)


@dataclass(frozen=True)
class DecisionsJunctionsRequireMultiOut(Rule):
    """Rule enforcing that Decision/Junction pseudostates are required to have >= 2 outgoing transitions."""

    description: str = "All Decision/Junction pseudostates are required to have >= 2 outgoing transitions."

    def evaluate(self, machine: StateMachine) -> None:
        """Evalute this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            IllegalStateError: If the state machine violates this rule.

        """
        flattened = machine.get_flattened_states()
        for s in flattened.values():
            if s.type in {StateType.DECISION, StateType.JUNCTION} and len(machine.get_outgoing_transitions(s)) < 2:
                raise IllegalStateError("Decision / Junction pseudostates must have >=2 outgoing transitions.", s, machine.name)


@dataclass(frozen=True)
class JoinsRequireMultiInSingleOut(Rule):
    """Rule enforcing that Join pseudostates are required to have >= 2 incoming transitions and exactly 1 outgoing transition."""

    description: str = "All Join pseudostates are required to have >= 2 incoming transitions and exactly 1 outgoing transition."

    def evaluate(self, machine: StateMachine) -> None:
        """Evalute this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            IllegalStateError: If the state machine violates this rule.

        """
        flattened = machine.get_flattened_states()
        for s in flattened.values():
            if s.type == StateType.JOIN:
                if len(machine.get_incoming_transitions(s)) < 2:
                    raise IllegalStateError("Join pseudostates must have >= 2 incoming transitions.", s, machine.name)
                if len(machine.get_outgoing_transitions(s)) != 1:
                    raise IllegalStateError("Join pseudostates must have exactly 1 outgoing transition.", s, machine.name)


@dataclass(frozen=True)
class ForksRequireSingleInMultiOut(Rule):
    """Rule enforcing that all Fork pseudostates are required to have exactly 1 incoming transition and >= 2 outgoing transitions."""

    description: str = "All Fork pseudostates are required to have exactly 1 incoming transition and >= 2 outgoing transitions."

    def evaluate(self, machine: StateMachine) -> None:
        """Evalute this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            IllegalStateError: If the state machine violates this rule.

        """
        flattened = machine.get_flattened_states()
        for s in flattened.values():
            if s.type == StateType.FORK:
                if len(machine.get_incoming_transitions(s)) != 1:
                    raise IllegalStateError("Fork pseudostates must have exactly 1 incoming transition.", s, machine.name)
                if len(machine.get_outgoing_transitions(s)) != 1:
                    raise IllegalStateError("Fork pseudostates must have >= 2 outgoing transitions.", s, machine.name)


@dataclass(frozen=True)
class AllStatesMustBeReachable(Rule):
    """Rule enforcing that all states (and substates) within the state machine must be reachable."""

    description: str = "All states (and substates) within the state machine must be reachable."

    def evaluate(self, machine: StateMachine) -> None:
        """Evalute this rule.

        Args:
            machine (StateMachine): The state machine being evaluated against.

        Raises:
            ValueError: If the state machine violates this rule.

        """
        root_state = machine.get_root()
        reachable_states = self._compute_reachable_states(root_state.name, machine.get_adjacency_list())
        all_states = set(machine.get_flattened_states())
        unreachable_states = all_states - reachable_states
        if unreachable_states:
            raise ValueError(f"Unreachable state(s) detected in state machine: {', '.join(unreachable_states)}")

    def _compute_reachable_states(self, root: str, adj: dict[str, list[str]]) -> set[str]:
        visited = set()
        stack = [root]
        while stack:
            s = stack.pop()
            if s in visited:
                continue
            visited.add(s)
            stack.extend(adj.get(s, []))
        return visited


# @dataclass(frozen=True)
# class CompositeStatesMustHaveOneInitialOneLeaf(Rule):
#     """Rule enforcing that all Composite states must minimally have 1 initial state and 1 leaf state."""

#     description: str = "All Composite states must minimally have 1 initial state and 1 leaf state."

ALL_RULES: list[RuleLike] = [
    StateNamesMustBeUnique(),
    EventNamesMustBeUnique(),
    ErrorNamesMustBeUnique(),
    StateIDSMustBeMonotonic(),
    EventIDSMustBeMonotonic(),
    ErrorIDSMustBeMonotonic(),
    NoTransitionIntoSimpleInitial(),
    TransitionsMustReferenceExistingSymbols(),
    NoTransitionOutOfFinalOrTerminal(),
    EntryExitStatesRequireParent(),
    DecisionsJunctionsRequireMultiOut(),
    JoinsRequireMultiInSingleOut(),
    ForksRequireSingleInMultiOut(),
    AllStatesMustBeReachable(),
]
