from __future__ import annotations

import logging
from collections import defaultdict
from copy import deepcopy
from functools import cached_property
from pathlib import Path
from typing import Annotated, Any, ClassVar, Self, TypeVar

import yaml
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, JsonValue, PrivateAttr, StrictInt, model_validator

from smal.schemas.action import Action  # noqa: TC001 - Pydantic requires this import at runtime
from smal.schemas.constant import Constant
from smal.schemas.context import ContextVar  # noqa: TC001 - Pydantic requires this import at runtime
from smal.schemas.debug import EnumSpec
from smal.schemas.enumeration import Enumeration, EnumMember
from smal.schemas.error import Error  # noqa: TC001 - Pydantic requires this import at runtime
from smal.schemas.event import Event  # noqa: TC001 - Pydantic requires this import at runtime
from smal.schemas.guard import GuardDef, GuardRef  # noqa: TC001 - Pydantic requires this import at runtime
from smal.schemas.state import State, StateType
from smal.schemas.transition import ShorthandTransitionMap, Transition
from smal.utilities import constants as SMALConstants
from smal.utilities import expressions as SMALExpressions
from smal.utilities.corrections import ALL_CORRECTIONS
from smal.utilities.rules import ALL_RULES
from smal.utilities.types import Identifier, SemVer, SMALPrimitive

CONTEXT_PRIMITIVES: frozenset[SMALPrimitive] = frozenset(p for p in SMALPrimitive if p.is_integer or p.is_float or p == SMALPrimitive.BOOL)
_EnumeratedObject = TypeVar("_EnumeratedObject", bound=State | EnumMember)
"""The SMAL primitives a context variable may use as its type. Enums are also allowed, by their bare name."""


class Machine(BaseModel):
    """Schema for a state machine defined in a SMAL (yaml) file.

    Constructing a Machine (e.g. `Machine(...)`, `Machine.model_validate(...)` or `Machine.blank(...)`) runs structural
    validation only: shorthand normalization, id assignment, name and reference checks, composite transition resolution,
    and building of the adjacency lists.

    WARNING: Construction does NOT apply corrections or evaluate rules. Those depend on the user's persistence
    settings, may read the persistence file, and may modify the machine, so they live in `analyze()`. You must call
    `analyze()` manually on any Machine you build directly if you want corrections and rules applied:

        machine = Machine.model_validate(data).analyze()

    `Machine.from_file()` calls `analyze()` for you.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", populate_by_name=True, arbitrary_types_allowed=True)

    name: Identifier = Field(alias="machine", description="The state machine name.")
    version: SemVer = Field(description="Semantic version (major.minor.patch) of this state machine.")
    states: list[State] = Field(description="States of this state machine.")
    enums: list[Enumeration] = Field(default_factory=list, description="Enums of this state machine.")
    events: list[Event] = Field(default_factory=list, description="Events of this state machine.")
    actions: list[Action] = Field(default_factory=list, description="Actions of this state machine.")
    errors: list[Error] = Field(default_factory=list, description="Errors of this state machine.")
    constants: list[Constant] = Field(default_factory=list, description="Constant values associated with this state machine.")
    context: list[ContextVar] = Field(default_factory=list, description="Context variables.")
    guards: Annotated[list[GuardDef], BeforeValidator(lambda v: [] if v is None else v)] = Field(
        default_factory=list,
        description="Guards of this state machine.",
    )
    transitions: list[Transition] = Field(default_factory=list, description="Transitions of this state machine.")
    description: str | None = Field(default=None, description="Description of this state machine.")
    metadata: dict[str, JsonValue] = Field(default_factory=dict, description="Metadata of this state machine.")
    _adj: dict[Identifier, list[Identifier]] = PrivateAttr(default_factory=lambda: defaultdict(list))
    _adj_rev: dict[Identifier, list[Identifier]] = PrivateAttr(default_factory=lambda: defaultdict(list))

    @property
    def initial_state(self) -> State:
        """Get the initial state of this state machine, which is the unique state that is not a substate of any other state and has type INITIAL.

        Returns:
            State: The initial State object of this state machine.

        """
        initial_states = [s for s in self.states if not s.is_substate and s.type == StateType.INITIAL]
        match len(initial_states):
            case 0:
                raise ValueError(
                    f"StateMachine '{self.name}' has no root initial state. \
                        A state machine must have exactly one root initial state (type: INITIAL and not a substate).",
                )
            case 1:
                return initial_states[0]
            case _:
                raise ValueError(
                    f"StateMachine '{self.name}' has multiple root initial states: {', '.join(s.name for s in initial_states)}."
                    " A state machine must have exactly one root initial state (type: INITIAL and not a substate).",
                )

    @property
    def root_state(self) -> State | None:
        """Get the root state of this state machine, which is the unique state that is not a substate of any other state and has no incoming transitions.

        NOTE: Not all state machines are guaranteed to have a root state, \
        for example, an indefinitely-running state machine that always lands back in its initial state.

        No state machine is allowed to have more than one root state, as that would violate the tree structure requirement for the state hierarchy.

        Returns:
            State | None: The root State object of this state machine, or None if no root state exists.

        """
        roots = [s for s in self.states if not s.is_substate and not s.is_composite and len(self.get_incoming_transitions(s)) == 0]
        match len(roots):
            case 0:
                return None
            case 1:
                return roots[0]
            case _:
                raise ValueError(
                    f"StateMachine '{self.name}' has multiple root states: {', '.join(s.name for s in roots)}. \
                        A state machine must have exactly one root state.",
                )

    @property
    def composite_states(self) -> list[State]:
        """Get all root-level composite states of this state machine.

        Returns:
            list[State]: All root-level composite states of this state machine.

        """
        return [s for s in self.states if s.is_composite]

    @property
    def adjacency_list(self) -> dict[Identifier, list[Identifier]]:
        """Get the adjacency list for this state machine, where keys are source state names and values are lists of target state names.

        Returns:
            dict[Identifier, list[Identifier]]: The adjacency list representing the transitions between states in this state machine.

        """
        return self._adj

    @cached_property
    def longest_action_chain(self) -> int:
        """Get the length of the longest chain of actions of any single transition in this state machine.

        Returns:
            int: The length of the longest action chain.

        """
        return max(len(t.actions) for t in self.transitions)

    def enum_specs(self, prefixes: dict[str, str] | None = None) -> list[EnumSpec]:
        """Get the enumeration specification for this state machine's enumerations.

        Returns:
            list[EnumSpec]: All enum specs for this state machine's enumerations.

        """
        return [e.specification(prefix=prefixes.get(e.name) if prefixes else None) for e in self.enums]

    def errors_enum_spec(
        self,
        prefix: str | None = None,
        storage: SMALPrimitive = SMALPrimitive.UINT32,
        flags: bool = False,
        include_null: bool = False,
        include_count: bool = False,
    ) -> EnumSpec:
        """Get the enumeration specification for this machine's errors.

        Args:
            prefix (str | None): Optional prefix to prepend to the enum member names. If None, defaults to '<machine_name>_error'.
            storage (SMALPrimitive): The storage type for the enum. Defaults to UINT32.
            flags (bool): Whether the enum should be treated as a flags enum. Defaults to False.
            include_null (bool): Whether to include a 'null' member in the enum. Defaults to False.
            include_count (bool): Whether to include a 'count' member in the enum. Defaults to False.

        Returns:
            EnumSpec: The enum spec for errors.

        """
        enum_name = f"{self.name}_error".lower()
        offset = int(include_null and not flags)
        return EnumSpec.build_from_data(
            {error.name: (error.value if error.value is not None else idx) + offset for idx, error in enumerate(self.errors)},
            name=enum_name,
            storage=storage,
            flags=flags,
            prefix=enum_name if prefix is None else prefix,
            include_null=include_null,
            include_count=include_count,
        )

    def events_enum_spec(
        self,
        prefix: str | None = None,
        storage: SMALPrimitive = SMALPrimitive.UINT32,
        flags: bool = False,
        include_null: bool = False,
        include_count: bool = False,
    ) -> EnumSpec:
        """Get the enumeration specification for this machine's events.

        Args:
            prefix (str | None): Optional prefix to prepend to the enum member names. If None, defaults to '<machine_name>_event'.
            storage (SMALPrimitive): The storage type for the enum. Defaults to UINT32.
            flags (bool): Whether the enum should be treated as a flags enum. Defaults to False.
            include_null (bool): Whether to include a 'null' member in the enum. Defaults to False.
            include_count (bool): Whether to include a 'count' member in the enum. Defaults to False.

        Returns:
            EnumSpec: The enum spec for events.

        """
        enum_name = f"{self.name}_event".lower()
        offset = int(include_null and not flags)
        return EnumSpec.build_from_data(
            {event.name: (event.value if event.value is not None else idx) + offset for idx, event in enumerate(self.events)},
            name=enum_name,
            storage=storage,
            flags=flags,
            prefix=enum_name if prefix is None else prefix,
            include_null=include_null,
            include_count=include_count,
        )

    def states_enum_spec(
        self,
        prefix: str | None = None,
        storage: SMALPrimitive = SMALPrimitive.UINT32,
        flags: bool = False,
        include_null: bool = False,
        include_count: bool = False,
    ) -> EnumSpec:
        """Get the enumeration specification for this machine's states.

        Args:
            prefix (str | None): Optional prefix to prepend to the enum member names. If None, defaults to '<machine_name>_state'.
            storage (SMALPrimitive): The storage type for the enum. Defaults to UINT32.
            flags (bool): Whether the enum should be treated as a flags enum. Defaults to False.
            include_null (bool): Whether to include a 'null' member in the enum. Defaults to False.
            include_count (bool): Whether to include a 'count' member in the enum. Defaults to False.

        Raises:
            ValueError: If any state has no ID.

        Returns:
            EnumSpec: The enum spec for states.

        """
        offset = int(include_null and not flags)
        state_data = {}
        for state in self.states:
            if state.value is None:
                raise ValueError("All states must have a value.")
            state_data[state.name] = state.value + offset
        state_enum_name = f"{self.name}_state".lower()
        return EnumSpec.build_from_data(
            state_data,
            name=state_enum_name,
            storage=storage,
            flags=flags,
            prefix=prefix or state_enum_name,
            include_null=include_null,
            include_count=include_count,
        )

    @model_validator(mode="before")
    @classmethod
    def normalize_shorthand_input(cls, v: Any) -> Any:
        """Normalize any cross-machine shorthand input before any other validation occurs.

        For example, events that are inferred from transitions but not explicitly defined in the events section.

        This allows users to write more concise SMAL files.

        """
        if not isinstance(v, dict):
            return v
        v: dict[str, Any] = dict(v)  # Don't mutate the caller's data
        # First, we need to normalize shorthand transitions
        raw_transitions = v.get("transitions")
        if raw_transitions is None:
            return v
        # Normalize transition map -> list[Transition]
        if isinstance(raw_transitions, dict):
            normalized_transitions = ShorthandTransitionMap(transitions=raw_transitions).to_transitions()
            v["transitions"] = normalized_transitions
        else:
            normalized_transitions = raw_transitions
        # Infer events from transitions if not explicitly defined
        events = v.get("events", [])
        if not events:
            inferred_evt_names: list[Identifier] = []
            for t in normalized_transitions:
                if isinstance(t, Transition):
                    names = (t.evt, t.tgt_entry_evt)
                elif isinstance(t, dict):
                    names = (t.get("evt"), t.get("tgt_entry_evt"))
                else:
                    continue
                # Completion transitions have no evt, so skip None values
                inferred_evt_names.extend(n for n in names if n)
            v["events"] = list(dict.fromkeys(inferred_evt_names))  # Remove duplicates while preserving order
        # Resolve shorthand constant representation
        if "constants" in v:
            constants = v.get("constants")
            if constants is None:
                v["constants"] = []
            elif isinstance(constants, dict):
                resolved_shorthand = [Constant(name=k, value=v) for k, v in constants.items()]
                v["constants"] = resolved_shorthand
        # Done
        return v

    @model_validator(mode="after")
    def enforce_monotonic_enumerations(self) -> Self:
        """Enforce that all enumerated objects (States, Events, Errors, Enums, etc.) are defined with monotonically increasing values.

        Returns:
            Self: The validated StateMachine instance with monotonic enumeration values enforced.

        """

        def enforce_monotonicity_helper(objects: list[_EnumeratedObject]) -> None:
            obj_type = type(objects[0]).__name__ if objects else "Object"
            values = [o.value for o in objects]
            if any(v is None for v in values):
                logging.debug(
                    "StateMachine '%s': Some %ss are missing values. Assigning fresh monotonic values based on order of definition.", self.name, obj_type
                )
                for idx, obj in enumerate(objects):
                    objects[idx] = obj.model_copy(update={"value": idx})
                    logging.debug("StateMachine '%s': Assigned value %d to %s '%s'.", self.name, idx, obj_type, obj.name)
                return
            sorted_values = sorted(values)
            expected_values = list(range(len(objects)))
            if sorted_values != expected_values:
                raise ValueError(
                    f"StateMachine '{self.name}': Object values must be monotonically increasing starting from 0. Found values: {values}."
                    f" Expected: {expected_values}."
                )
            return

        # Enforce monotonic IDs for states, events and errors
        enforce_monotonicity_helper(self.states)
        enforce_monotonicity_helper(self.events)
        enforce_monotonicity_helper(self.errors)
        # TODO: self.enums
        # Done
        return self

    @model_validator(mode="after")
    def enforce_unique_names(self) -> Self:
        """Enforce that all named objects (States, Events, Errors, etc.) are defined with globally unique names.

        Returns:
            Self: The validated StateMachine instance with unique names enforced.

        """
        name_to_objects: dict[str, list[Any]] = defaultdict(list)
        for state in self.states:
            name_to_objects[state.name].append(state)
        for event in self.events:
            name_to_objects[event.name].append(event)
        for error in self.errors:
            name_to_objects[error.name].append(error)
        # Enum type names share the machine-wide namespace. Enum *member* names deliberately do not (they only need to be unique within their enum).
        for enum in self.enums:
            name_to_objects[enum.name].append(enum)
        duplicates = {name: objs for name, objs in name_to_objects.items() if len(objs) > 1}
        if duplicates:
            duplicate_messages = []
            for name, objs in duplicates.items():
                obj_types = ", ".join(type(o).__name__ for o in objs)
                duplicate_messages.append(f"Name '{name}' is used by multiple objects of types: {obj_types}")
            raise ValueError(f"StateMachine '{self.name}': Duplicate names found across objects. " + "; ".join(duplicate_messages))
        return self

    @model_validator(mode="after")
    def enforce_valid_transition_references(self) -> Self:
        """Enforce that all transition references are made to valid, existing objects within the state machine.

        Returns:
            Self: The validated StateMachine instance with valid transition references enforced.

        """
        state_map = self.flatten(self.states)
        event_names = {e.name for e in self.events}
        for t in self.transitions:
            if t.src not in state_map:
                raise ValueError(f"StateMachine '{self.name}': Transition from '{t.src}' references a state that does not exist.")
            if t.tgt and t.tgt not in state_map:
                raise ValueError(f"StateMachine '{self.name}': Transition to '{t.tgt}' references a state that does not exist.")
            if t.evt and t.evt not in event_names:
                raise ValueError(f"StateMachine '{self.name}': Transition event '{t.evt}' references an event that does not exist.")
            if t.tgt_entry_evt and t.tgt_entry_evt not in event_names:
                raise ValueError(f"StateMachine '{self.name}': Transition target entry event '{t.tgt_entry_evt}' references an event that does not exist.")
            for action in t.actions:
                all_actions = {a.name for a in self.actions}
                if action.name not in all_actions:
                    raise ValueError(f"StateMachine '{self.name}': Transition action '{action}' references an action that does not exist.")
        return self

    @model_validator(mode="after")
    def resolve_composite_transitions(self) -> Self:
        """Resolve any transitions that directly utilize a composite state to instead target that composite's internal initial substate.

        Returns:
            Self: The validated StateMachine instance with composite transition targets resolved.

        """
        for t in self.transitions:
            # We want to consider transitions that use a composite state as a source as well as a target
            src_state = self.get_state(t.src)
            if src_state.type == StateType.COMPOSITE:
                initial_substate_name = src_state.initial_substate.name
                logging.warning(
                    "StateMachine '%s': Transition from composite state '%s' detected. Redirecting from internal initial substate '%s'...",
                    self.name,
                    t.src,
                    initial_substate_name,
                )
                t.set_original_src(t.src)
                t.src = initial_substate_name
            # Targets... (internal transitions have no target to resolve)
            if t.tgt is None:
                continue
            tgt_state = self.get_state(t.tgt)
            if tgt_state.type == StateType.COMPOSITE:
                initial_substate_name = tgt_state.initial_substate.name
                logging.warning(
                    "StateMachine '%s': Transition from '%s' to composite state '%s' detected. Redirecting to internal initial substate '%s'...",
                    self.name,
                    t.src,
                    t.tgt,
                    initial_substate_name,
                )
                t.set_original_tgt(t.tgt)
                t.tgt = initial_substate_name
        return self

    @model_validator(mode="after")
    def validate_simple_structural_invariants(self) -> Self:
        """Validate simple structural invariants for the state machine.

        Examples:
        - At least one state is defined.
        - At least one root initial state is defined (type: INITIAL and not a substate).
        - No more than one root initial state is defined (type: INITIAL and not a substate).

        Raises:
            ValueError: If no states are defined.
            ValueError: If no root initial state is defined.
            ValueError: If multiple root initial states are defined.

        Returns:
            Self: The validated StateMachine instance with structural invariants enforced.

        """
        if not self.states:
            raise ValueError(f"StateMachine '{self.name}' must have at least one state defined.")
        root_initial_states = [s for s in self.states if s.type == StateType.INITIAL and not s.is_substate]
        match len(root_initial_states):
            case 0:
                raise ValueError(f"StateMachine '{self.name}' must have at least one root initial state defined (type: INITIAL and not a substate).")
            case 1:
                pass  # Valid
            case _:
                raise ValueError(
                    f"StateMachine '{self.name}' must have exactly one root initial state defined (type: INITIAL and not a substate)."
                    f" Found: {', '.join(s.name for s in root_initial_states)}",
                )
        return self

    @model_validator(mode="after")
    def enforce_context_types(self) -> Self:
        """Enforce that all context variables declare valid types and values.

        Raises:
            ValueError: If context variable has invalid enum default.
            ValueError: If context variable has redundant value constraints.
            ValueError: If context variable has unknown type.

        Returns:
            Self: The validated machine.

        """
        for e in self.enums:
            if SMALPrimitive.is_smal_primitive(e.name):
                raise ValueError(f"Enum name '{e.name}' collides with a SMAL primitive type.")
        for c in self.context:
            try:
                resolved = self.resolve_context_type(c.type)
            except ValueError as exc:
                raise ValueError(f"Context variable '{c.name}': {exc}") from exc
            if isinstance(resolved, Enumeration):
                if not isinstance(c.default_value, str) or c.default_value not in resolved.resolved_values:
                    raise ValueError(f"Context variable '{c.name}' default value '{c.default_value}' is not a member of enum '{c.type}'.")
                if c.value_constraints:
                    raise ValueError(f"Context variable '{c.name}' is an enum type, value_constraints is redundant.")
                c.set_resolved_type(resolved)
                resolved_value = next((v for v in resolved.values if v.name == c.default_value), None)
                c.set_resolved_value(resolved_value)
                continue
            try:
                resolved.check_value(c.default_value)
                for allowed in c.value_constraints or []:
                    resolved.check_value(allowed)
            except ValueError as exc:
                raise ValueError(f"Context variable '{c.name}' ({resolved.value}): {exc}") from exc
            if c.value_constraints and c.default_value not in c.value_constraints:
                raise ValueError(f"Context variable '{c.name}': default value {c.default_value!r} is not one of its value_constraints {c.value_constraints}.")
            c.set_resolved_type(resolved)
            c.set_resolved_value(c.default_value)
        return self

    def resolve_context_type(self, type_name: str) -> SMALPrimitive | Enumeration:
        """Resolve the `type` of a context variable to a SMAL primitive or one of this machine's enums.

        Args:
            type_name (str): The type as written in the SMAL file: a fixed-width integer, float32, float64, bool, or the bare name of an enum.

        Raises:
            ValueError: If the type is unknown, is a SMAL primitive that context variables can't use, or is written as `enum:<name>`.

        Returns:
            SMALPrimitive | Enumeration: The primitive, or the enum with that name.

        """
        for enum in self.enums:
            if enum.name == type_name:
                return enum
        if type_name.startswith("enum:"):
            raise ValueError(f"Type '{type_name}' should be written as the enum's bare name, '{type_name.partition(':')[2]}'.")
        allowed = ", ".join(sorted(p.value for p in CONTEXT_PRIMITIVES))
        if SMALPrimitive.is_smal_primitive(type_name):
            primitive, _ = SMALPrimitive.from_str(type_name)
            if primitive in CONTEXT_PRIMITIVES:
                return primitive
            raise ValueError(f"Type '{type_name}' is not supported for context variables. Expected one of: {allowed}, or the name of an enum.")
        raise ValueError(f"Unknown type '{type_name}'. Expected one of: {allowed}, or the name of an enum declared in `enums`.")

    @model_validator(mode="after")
    def enforce_expressions_and_guard_references(self) -> Self:
        """Enforce that guard and action expressions only use known names, and that transitions only use declared guards.

        Raises:
            ValueError: If an expression refers to a name that is not a context variable, constant or enum member.
            ValueError: If an action sets something that is not a context variable, or assigns a non-member to an enum variable.
            ValueError: If a transition uses a guard that is not declared in `guards`.

        Returns:
            Self: The validated StateMachine instance.

        """
        context_by_name = {c.name: c for c in self.context}
        constant_names = {c.name for c in self.constants}
        known_names = set(context_by_name) | constant_names | {m for e in self.enums for m in e.resolved_values}

        def check_names(expression: str, where: str) -> None:
            unknown = sorted(SMALExpressions.referenced_names(SMALExpressions.parse(expression)) - known_names)
            if unknown:
                raise ValueError(
                    f"StateMachine '{self.name}': {where} refers to unknown names {unknown}. Expected context variables, constants or enum members.",
                )

        for g in self.guards:
            if g.expr is not None:
                check_names(g.expr, f"guard '{g.name}'")
        for a in self.actions:
            for var, value in a.sets.items():
                if var not in context_by_name:
                    raise ValueError(f"StateMachine '{self.name}': action '{a.name}' sets '{var}', which is not a context variable.")
                resolved = self.resolve_context_type(context_by_name[var].type)
                if not isinstance(value, str):
                    # A literal assignment: check that it fits the variable's type
                    if isinstance(resolved, Enumeration):
                        raise TypeError(
                            f"StateMachine '{self.name}': action '{a.name}' assigns the literal {value!r} to enum variable '{var}'. "
                            f"Assign one of its members ({', '.join(resolved.resolved_values)}) instead.",
                        )
                    try:
                        resolved.check_value(value)
                    except ValueError as exc:
                        raise ValueError(f"StateMachine '{self.name}': action '{a.name}' assignment to '{var}': {exc}") from exc
                    continue
                check_names(value, f"action '{a.name}' assignment to '{var}'")
                enum = resolved if isinstance(resolved, Enumeration) else None
                member = SMALExpressions.bare_name(value)
                if (
                    enum is not None
                    and member is not None
                    and member not in context_by_name
                    and member not in constant_names
                    and member not in enum.resolved_values
                ):
                    raise ValueError(
                        f"StateMachine '{self.name}': action '{a.name}' assigns '{member}' to '{var}', which is not a member of enum '{enum.name}' "
                        f"({', '.join(enum.resolved_values)}).",
                    )
        declared_guards = {g.name for g in self.guards}
        for t in self.transitions:
            for ref in t.guard:
                if ref.name not in declared_guards:
                    raise ValueError(f"StateMachine '{self.name}': transition from '{t.src}' uses guard '{ref.name}', which is not declared in guards.")
        return self

    @model_validator(mode="after")
    def build_derived_data(self) -> Self:
        """Build data derived from the validated machine.

        This must be the last `after` validator: Pydantic runs `after` validators in definition order, so by now
        ids are assigned, references are checked and composite transitions are redirected.

        Returns:
            Self: The machine with its derived data (adjacency lists) built.

        """
        self._build_derived_data()
        return self

    def _build_derived_data(self) -> None:
        """(Re)build the forward and reverse adjacency lists from the current transitions."""
        self._adj = defaultdict(list)
        self._adj_rev = defaultdict(list)
        for t in self.transitions:
            if t.tgt is not None:  # Internal transitions don't create graph edges
                self._adj[t.src].append(t.tgt)
                self._adj_rev[t.tgt].append(t.src)
        # Add implicit composite state entry edges
        # Precompute least common ancestors

    def analyze(self) -> Self:
        """Apply corrections, then evaluate rules, according to the user's persistence settings.

        This is deliberately not part of model construction, because it reads the persistence file and may mutate the machine.
        `from_file` calls it. Anything that builds a Machine directly (`Machine(...)`, `model_validate`, `blank`) must call it explicitly.

        Returns:
            Self: This machine, to allow chaining.

        """
        from smal.utilities.persistence import SMALPersistence, get_loading_settings

        # If a persistence file is currently being deserialized, reuse its rules/corrections settings instead of
        # calling `SMALPersistence.load()` again, which would try to deserialize this very machine and recurse forever.
        loading_settings = get_loading_settings()
        if loading_settings is not None:
            rules_settings, corrections_settings = loading_settings
        else:
            persistence = SMALPersistence.load() if SMALPersistence.DEFAULT_PATH.exists() else SMALPersistence()
            rules_settings, corrections_settings = persistence.rules, persistence.corrections
        # Apply all corrections before validating
        for correction in ALL_CORRECTIONS:
            correction_enabled = corrections_settings.get(correction.name, True)
            if not correction_enabled:
                logging.info("Skipping correction '%s' because it is disabled in persistence settings.", correction.name)
                continue
            logging.info("Applying correction: %s", correction.name)
            correction.pre_application(self)
            correction.apply(self)
            logging.info("Correction '%s' applied", correction.name)
            correction.post_application(self)
        # Corrections may have changed transitions, so refresh the derived data before evaluating rules
        self._build_derived_data()
        # Evaluate all rules to validate
        for rule in ALL_RULES:
            rule_enabled = rules_settings.get(rule.name, True)
            if not rule_enabled:
                logging.info("Skipping rule '%s' because it is disabled in persistence settings.", rule.name)
                continue
            logging.info("Evaluating rule: %s", rule.name)
            rule.pre_evaluation(self)
            rule.evaluate(self)
            logging.info("Rule '%s' satisfied", rule.name)
            rule.post_evaluation(self)
        return self

    @staticmethod
    def flatten(states: list[State]) -> dict[Identifier, State]:
        """Get a flattened dictionary of all states (including substates) from the given list.

        Args:
            states (list[State]): The list of states to flatten, which may include composite states with substates.

        Returns:
            dict[Identifier, State]: The flattened dictionary mapping state names to State objects, including all substates.

        """
        flat: dict[Identifier, State] = {}
        for s in states:
            flat[s.name] = s
            if s.substates:
                flat.update(Machine.flatten(s.substates))
        return flat

    @classmethod
    def blank(cls, name: Identifier = "NULL", version: SemVer = "0.0.0", states: list[State] | None = None) -> Self:
        """Create a blank StateMachine instance with the given name and version, a single initial state, no events or transitions.

        Args:
            name (Identifier, optional): The name of the state machine. Defaults to "NULL".
            version (SemVer, optional): The semantic version of the state machine. Defaults to "0.0.0".
            states (list[State] | None, optional): An optional list of states to initialize the state machine with. \
                Defaults to None, which results in an empty list of states.

        Returns:
            Self: A blank StateMachine instance.

        """
        return cls(name=name, version=version, states=states or [State(name="initial", type=StateType.INITIAL)])

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        """Instantiate a StateMachine/SMALFile from the file at the given path.

        Args:
            path (str | Path): The file path to read the state machine definition from. Must have a supported SMAL file extension.

        Raises:
            ValueError: If the file does not have a supported SMAL file extension.
            FileNotFoundError: If the file does not exist.

        Returns:
            Self: The StateMachine instance created from the file.

        """
        path = Path(path)
        try:
            if not SMALConstants.SupportedFileExtensions.is_smal_file(path, check_exists=True):
                raise ValueError(f"SMAL file must have one of the following extensions: {', '.join(SMALConstants.SupportedFileExtensions.all())}")
        except FileNotFoundError:  # noqa: TRY203 - Remove exception handler, error is immediately re-raised
            raise
        yaml_data = path.read_text(encoding="utf-8")
        model_data = yaml.safe_load(yaml_data)
        return cls.model_validate(model_data).analyze()

    def get_state(self, name: Identifier) -> State:
        """Get a state by name from this state machine.

        Args:
            name (Identifier): The name of the state to retrieve.

        Returns:
            State: The State object with the given name.

        """
        state_map = self.flatten(self.states)
        if name not in state_map:
            raise KeyError(f"State '{name}' not found in state machine '{self.name}'.")
        return state_map[name]

    def get_incoming_transitions(self, state: Identifier | State) -> list[Transition]:
        """Get all incoming transitions to the given state.

        Args:
            state (Identifier | State): The name of the target state or the State object itself.

        Returns:
            list[Transition]: A list of Transition objects that have the given state as their target.

        """
        state_name = state if isinstance(state, str) else state.name
        return [t for t in self.transitions if t.tgt == state_name]

    def get_outgoing_transitions(self, state: Identifier | State) -> list[Transition]:
        """Get all outgoing transitions from the given state.

        Args:
            state (Identifier | State): The name of the source state or the State object itself.

        Returns:
            list[Transition]: A list of Transition objects that have the given state as their source.

        """
        state_name = state if isinstance(state, str) else state.name
        return [t for t in self.transitions if t.src == state_name]

    def get_ordered_flat_global_state_list(self) -> list[State]:
        """Get an ordered, flattened list of all states and substates.

        NOTE: Substates are defined after their respective superstates, and inherit the resulting ordinal ID.

        Returns:
            list[State]: The ordered, flattened list of all states and substates.

        """

        # Recursive helper to flatten the states
        def helper() -> list[State]:
            ordered: list[State] = []

            def walk(state: State) -> None:
                ordered.append(state)
                for sub in sorted(state.substates, key=lambda s: s.value or 0):
                    walk(sub)

            # Walk all top-level states in sorted order
            for state in sorted(self.states, key=lambda s: s.value or 0):
                walk(state)
            return ordered

        # Deepcopy so we don't alter the originals
        states = deepcopy(helper())
        # Ensure all flat states are now monotonically increasing value
        for i, state in enumerate(states):
            state.value = i
        # Done
        return states

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
        """Serialize this StateMachine to a SMAL file.

        Args:
            path (str | Path): The file path to write the state machine definition to. Must have a supported SMAL file extension.
            exclude_unset (bool, optional): Whether to exclude unset fields from the output. Defaults to False.
            exclude_defaults (bool, optional): Whether to exclude fields with default values from the output. Defaults to False.
            exclude_none (bool, optional): Whether to exclude fields with None values from the output. Defaults to True.
            exclude_computed_fields (bool, optional): Whether to exclude computed fields from the output. Defaults to False.
            sort_keys (bool, optional): Whether to sort the keys in the output. Defaults to False.
            indent (int, optional): The number of spaces to use for indentation in the output. Defaults to 2.

        Raises:
            ValueError: If the file does not have a supported SMAL file extension.

        """
        path = Path(path)
        if not SMALConstants.SupportedFileExtensions.is_smal_file(path, check_exists=False):
            raise ValueError(f"SMAL file must have one of the following extensions: {', '.join(SMALConstants.SupportedFileExtensions.all())}")
        # mode="json" converts enums etc. to plain values that yaml.safe_dump can represent
        model_data = self.model_dump(
            mode="json",
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            exclude_computed_fields=exclude_computed_fields,
        )
        # Restore transitions that were redirected to a composite's initial substate during validation.
        # This patches only the output, so this machine instance is left untouched.
        for t, t_data in zip(self.transitions, model_data.get("transitions", []), strict=True):
            if t.original_src is not None:
                t_data["src"] = t.original_src
            if t.original_tgt is not None:
                t_data["tgt"] = t.original_tgt
        yaml_data = yaml.safe_dump(model_data, sort_keys=sort_keys, indent=indent)
        path.write_text(yaml_data, encoding="utf-8")

    def enumerate_paths(self, start: Identifier | None = None, feasible_only: bool = True) -> list[list[Transition]]:
        """Enumerate every simple path from `start`, stopping at dead ends or at the edge that closes a cycle.

        With `feasible_only`, the context starts at its default values and is updated by each action's `sets` along the
        way, and a transition is only followed if its guards can hold at that point. This is conservative: it only drops
        paths that are definitely impossible. A guard is treated as possibly true or false (so its transition is kept) if
        it has no `expr`, or if its expression uses a variable that an internal transition can change at any time.

        An `else` transition is feasible unless a sibling (same source and event) is definitely enabled. Siblings are assumed
        to be mutually exclusive, so taking a guarded transition does not require its siblings' guards to be false.

        Args:
            start (Identifier | None, optional): The state to start from. Defaults to the root initial state.
            feasible_only (bool, optional): Whether to drop paths that guard logic makes impossible. Defaults to True.

        Raises:
            ValueError: If, with `feasible_only`, an action assigns a value that does not fit its variable's type (such as an integer overflow).
                Paths stop at the first repeated state, so an overflow that would only happen after looping many times is not detected.

        Returns:
            list[list[Transition]]: The paths, each a list of transitions in order.

        """
        start = start or self.initial_state.name
        outgoing: dict[str, list[Transition]] = defaultdict(list)
        siblings: dict[tuple[str, str | None], list[Transition]] = defaultdict(list)
        for t in self.transitions:
            siblings[(t.src, t.evt)].append(t)
            if t.tgt is not None:  # Internal transitions don't move between states
                outgoing[t.src].append(t)
        guard_exprs = {g.name: g.expr for g in self.guards}
        action_sets = {a.name: a.sets for a in self.actions}
        constants = {c.name: c.value for c in self.constants}
        context_types = {c.name: self.resolve_context_type(c.type) for c in self.context}
        # Variables an internal transition can change at any time, so guards that depend on them can't be decided from the path alone
        volatile = {var for t in self.transitions if t.tgt is None for a in t.actions for var in action_sets.get(a.name, {})}

        def guard_value(ref: GuardRef, context: dict[str, Any]) -> bool | None:
            expr = guard_exprs.get(ref.name)
            if expr is None:
                return None
            tree = SMALExpressions.parse(expr)
            if SMALExpressions.referenced_names(tree) & volatile:
                return None
            value = bool(SMALExpressions.evaluate(tree, {**constants, **context}))
            return not value if ref.negate else value

        def transition_guard(t: Transition, context: dict[str, Any]) -> bool | None:
            values = [guard_value(ref, context) for ref in t.guard]
            if False in values:
                return False
            if None in values:
                return None
            return True

        def is_feasible(t: Transition, context: dict[str, Any]) -> bool:
            if t.is_else:
                others = (s for s in siblings[(t.src, t.evt)] if s is not t and not s.is_else)
                return not any(transition_guard(s, context) is True for s in others)
            return transition_guard(t, context) is not False

        def check_assignment(action: str, var: str, value: Any) -> None:
            resolved = context_types[var]
            try:
                if isinstance(resolved, Enumeration):
                    if value not in resolved.resolved_values:
                        raise ValueError(f"{value!r} is not a member of enum '{resolved.name}'.")
                else:
                    resolved.check_value(value)
            except ValueError as exc:
                raise ValueError(f"StateMachine '{self.name}': action '{action}' sets '{var}' to a value that does not fit its type: {exc}") from exc

        def apply_actions(t: Transition, context: dict[str, Any]) -> dict[str, Any]:
            updated = dict(context)
            for a in t.actions:
                for var, value in action_sets.get(a.name, {}).items():
                    new_value = SMALExpressions.evaluate_source(value, {**constants, **updated}) if isinstance(value, str) else value
                    check_assignment(a.name, var, new_value)
                    updated[var] = new_value
            return updated

        paths: list[list[Transition]] = []

        def dfs(state: Identifier, visited: frozenset[str], path: list[Transition], context: dict[str, Any]) -> None:
            successors = [t for t in outgoing.get(state, []) if not feasible_only or is_feasible(t, context)]
            if not successors:
                paths.append(path)  # Dead end, such as a final state
                return
            for t in successors:
                if t.tgt in visited:
                    paths.append([*path, t])  # This edge closes a cycle, so stop here
                else:
                    next_context = apply_actions(t, context) if feasible_only else context
                    dfs(t.tgt, visited | {t.tgt}, [*path, t], next_context)

        dfs(start, frozenset({start}), [], {c.name: c.default_value for c in self.context})
        return paths
