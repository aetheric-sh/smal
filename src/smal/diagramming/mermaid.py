"""Methods for rendering Mermaid diagrams from SMAL machines."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from smal.schemas.machine import Identifier, Machine, StateType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from smal.schemas.machine import Transition


def _transition_label(t: Transition, include_actions: bool) -> str:
    """Build the `evt [guards] / actions` label for a transition.

    Args:
        t (Transition): The transition to label.
        include_actions (bool): Whether to append the transition's actions.

    Raises:
        ValueError: If the transition has no event but is not a completion transition.

    Returns:
        str: The label, which is empty for an unguarded completion transition without actions.

    """
    # Start with the triggering event, or blank if it's a completion transition
    label = t.evt or ""
    if label == "" and not t.is_completion:
        raise ValueError("Transition incorrectly identified as completion.")
    # If there are guards, add them to the label
    if t.guard:
        label += " [" + ", ".join(f"{'!' if g.negate else ''}{g.name}" for g in t.guard) + "]"
    elif t.is_else:
        label += " [else]"
    # If there are actions, add them
    if include_actions and t.actions:
        label += " / " + ", ".join(a.name for a in t.actions)
    return label.strip()


def _wrap_description(description: str, width: int | None) -> list[str]:
    """Split a state description into note lines, keeping its paragraphs and wrapping long lines.

    Args:
        description (str): The description text.
        width (int | None): Maximum characters per line, or None to leave lines as they are.

    Returns:
        list[str]: The non-empty lines for the note body.

    """
    lines: list[str] = []
    for paragraph in description.splitlines():
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        lines.extend(textwrap.wrap(paragraph, width=width) if width else [paragraph])
    return lines


def render_mermaid_diagram(
    machine: Machine,
    file: str | Path | None = None,
    direction: Literal["LR", "TB"] = "LR",
    theme: Literal["default", "dark", "forest", "neutral", "base"] = "default",
    look: Literal["classic", "handDrawn", "neo"] = "classic",
    layout: Literal["dagre", "elk"] = "dagre",
    title: str | None = None,
    notes: dict[tuple[Identifier, Literal["left", "right"]], str] | None = None,
    indent: int = 4,
    action_display: Literal["table", "notes", "edges", "none"] = "table",
    inline_self_loops: bool = False,
    note_wrap_width: int | None = 40,
) -> str:
    """Render a Machine as a Mermaid stateDiagram-v2.

    Args:
        machine (Machine): The machine to render.
        file (str | Path, optional): Output file.
        direction (Literal["LR", "TB"], optional): Layout direction. Defaults to "LR".
        theme (str, optional): Mermaid theme. Defaults to "default".
        look (str, optional): Mermaid look. Defaults to "classic".
        layout (str, optional): Mermaid layout engine. Defaults to "dagre".
        title (str | None, optional): Diagram title. None uses the machine name and an empty string omits the title.
        notes (dict | None, optional): Extra notes keyed by (state, "left" | "right"). Defaults to None.
        indent (int, optional): Spaces per indentation level. Defaults to 4.
        action_display (ActionDisplay, optional): Where transition actions are shown. "notes" puts them in a note on the source
            state (one line per action) to keep edge labels short. "edges" puts them in the edge labels. "none" omits them.
            "table" also omits them from the diagram, because they belong in the Markdown table from `render_action_table`
            (see `render_mermaid_markdown`, which produces both together). In "notes" mode, actions on transitions out of
            decision states stay on the edge, since notes don't attach reliably to choice nodes. Defaults to "notes".
        inline_self_loops (bool, optional): Also render self-transitions (src == tgt) as a note instead of loop edges.
            Internal transitions (no target) are always rendered as a note on the left of the state. Self-transitions are external in UML, which
            exit and re-enter the state, so this is off by default. Defaults to False.
        note_wrap_width (int | None, optional): Maximum characters per line when a state's description is rendered as a note. A note is
            as wide as its longest line, and Mermaid has no width setting for notes. None disables wrapping. Defaults to 40.

    Returns:
        str: The Mermaid diagram source. A state's description, if it has one, is rendered as a note on the left of the state.

    """
    indent_str = " " * indent
    # NOTE: The title is a top-level frontmatter key. Mermaid ignores it inside `config`.
    config = {"theme": theme, "look": look, "layout": layout}
    title_lines = [f"title: {machine.name if title is None else title}"] if title != "" else []
    config_lines = ["---", *title_lines, "config:", *[f"{indent_str}{k}: {v}" for k, v in config.items()], "---"]
    retval = [*config_lines, "stateDiagram-v2", f"{indent_str}direction {direction}"]
    state_types = {name: s.type for name, s in Machine.flatten(machine.states).items()}
    for s in machine.states:
        if s.type in {StateType.INITIAL, StateType.ENTRY}:
            # NOTE: Entry should only be of this form inside of a composite state
            retval.append(f"{indent_str}[*] --> {s.name}")
        if s.type in {StateType.FINAL, StateType.TERMINAL, StateType.EXIT}:
            # NOTE: Exit should only be of this form inside of a composite state
            retval.append(f"{indent_str}{s.name} --> [*]")
        if s.type in {StateType.DECISION, StateType.JUNCTION}:
            retval.append(f"{indent_str}state {s.name} <<choice>>")
        if s.type == StateType.JOIN:
            retval.append(f"{indent_str}state {s.name} <<join>>")
        if s.type == StateType.FORK:
            retval.append(f"{indent_str}state {s.name} <<fork>>")
        if s.type == StateType.COMPOSITE:
            # TODO: Implement me, likely requires recursive substate handling
            pass
    for (s_id, loc), note in (notes or {}).items():
        retval.append(f"{indent_str}note {loc} of {s_id}: {note}")

    # Sort transitions into merged edges, internal state text and per-state action notes
    edges: dict[tuple[str, str], list[str]] = {}
    internal_text: dict[str, list[str]] = {}
    action_notes: dict[str, list[str]] = {}
    for t in machine.transitions:
        from_choice = state_types.get(t.src) in {StateType.DECISION, StateType.JUNCTION}
        # Internal activity belongs inside the state box, so it always carries its actions (unless actions are hidden)
        if t.tgt is None or (inline_self_loops and t.tgt == t.src):
            # Same layout as the action notes: the event on one line, then one "- action" line per action.
            # In "none" and "table" modes only the event is shown (the table lists the actions).
            show_actions = action_display in {"notes", "edges"} and bool(t.actions)
            label = _transition_label(t, include_actions=False)
            block = "\n".join([f"{label}:" if show_actions else label, *(f"- {a.name}" for a in t.actions if show_actions)])
            internal_text.setdefault(t.src, []).append(block)
            continue
        inline_actions = action_display == "edges" or (action_display == "notes" and from_choice)
        edges.setdefault((t.src, t.tgt), []).append(_transition_label(t, include_actions=inline_actions))
        if action_display == "notes" and t.actions and not from_choice:
            # One line for the event, then one "- action" line per action, so the note's width is set by the longest action name.
            # (A leading "- " is used instead of indentation because Mermaid may trim leading whitespace in note lines.)
            block = "\n".join([f"{_transition_label(t, include_actions=False)}:", *(f"- {a.name}" for a in t.actions)])
            action_notes.setdefault(t.src, []).append(block)

    # Parallel edges between the same two states become one edge with stacked labels
    for (src, tgt), labels in edges.items():
        text = "<br/>".join(dict.fromkeys(lbl for lbl in labels if lbl))
        retval.append(f"{indent_str}{src} --> {tgt}" + (f" : {text}" if text else ""))
    # A state's description and its internal activity share one note on the left of the state, description first.
    # (A `state : text` line would replace the state's name.) Action notes go on the right, so the two don't overlap.
    left_notes: dict[str, list[str]] = {}
    for s in machine.states:
        if s.description:
            left_notes[s.name] = _wrap_description(s.description, note_wrap_width)
    for src, blocks in internal_text.items():
        lines = left_notes.setdefault(src, [])
        lines.append("internal:")
        for block in dict.fromkeys(blocks):
            lines.extend(block.split("\n"))
    for src, lines in left_notes.items():
        retval.append(f"{indent_str}note left of {src}")
        retval.extend(f"{indent_str * 2}{line}" for line in lines)
        retval.append(f"{indent_str}end note")
    for src, blocks in action_notes.items():
        retval.append(f"{indent_str}note right of {src}")
        for block in dict.fromkeys(blocks):  # Drop duplicate event blocks, preserving order
            retval.extend(f"{indent_str * 2}{line}" for line in block.split("\n"))
        retval.append(f"{indent_str}end note")
    out = "\n".join(retval)
    if file:
        Path(file).write_text(out, encoding="utf-8")
    return out


def render_action_table(machine: Machine) -> str:
    """Render the actions of every transition as a Markdown table.

    Only transitions that have actions get a row. Actions are numbered in the order they execute.

    Args:
        machine (Machine): The machine to render.

    Returns:
        str: The Markdown table, or a short note if no transition has actions.

    """
    rows = []
    for t in machine.transitions:
        if not t.actions:
            continue
        trigger = _transition_label(t, include_actions=False) or "(completion)"
        target = t.tgt or "(internal)"
        actions = "<br>".join(f"{i}. {a.name}" for i, a in enumerate(t.actions, start=1))
        rows.append(f"| {t.src} | {trigger} | {target} | {actions} |")
    if not rows:
        return "_No transition actions._"
    return "\n".join(["| State | Trigger | Target | Actions (in order) |", "| --- | --- | --- | --- |", *rows])


def render_mermaid_markdown(machine: Machine, **diagram_options: Any) -> str:
    """Render a Markdown document containing the diagram and a table of transition actions.

    This is the way to use `action_display="table"`: the diagram omits actions and the table lists them.

    Args:
        machine (Machine): The machine to render.
        **diagram_options (Any): Options for `render_mermaid_diagram`. Any `action_display` given is ignored and set to "table".
            If `file` is given, the whole Markdown document (not just the diagram) is written there, and it must be a `.md` file.

    Raises:
        ValueError: If `file` is given and does not have a `.md` extension.

    Returns:
        str: The Markdown source, with the diagram in a ```mermaid fenced block followed by the action table.

    """
    # Handle `file` here rather than passing it through, which would write only the diagram source into the file
    file = diagram_options.pop("file", None)
    path = Path(file) if file else None
    if path is not None and path.suffix.lower() != ".md":
        raise ValueError(f"Markdown output must be written to a .md file, got '{path}'.")
    diagram = render_mermaid_diagram(machine, **{**diagram_options, "action_display": "table"})
    out = f"```mermaid\n{diagram}\n```\n\n## Transition actions\n\n{render_action_table(machine)}\n"
    if path is not None:
        path.write_text(out, encoding="utf-8")
    return out


def render_path_diagrams(
    machine: Machine,
    paths: Sequence[Sequence[Transition]],
    directory: str | Path | None = None,
    direction: Literal["LR", "TB"] = "LR",
    theme: Literal["default", "dark", "forest", "neutral", "base"] = "default",
    look: Literal["classic", "handDrawn", "neo"] = "classic",
    layout: Literal["dagre", "elk"] = "dagre",
    show_actions: bool = False,
    indent: int = 4,
    note_wrap_width: int | None = 40,
) -> list[str]:
    """Render one Mermaid stateDiagram-v2 per path, as returned by `Machine.enumerate_paths`.

    Each diagram contains only the states and transitions on its path, and every edge label starts with its step number
    so the order is clear. A path that ends by returning to a state it already visited is marked in the title.
    A state on the path that has a description gets it as a note on its left, like in `render_mermaid_diagram`.

    Args:
        machine (Machine): The machine the paths belong to.
        paths (Sequence[Sequence[Transition]]): The paths to render, e.g. `machine.enumerate_paths()`. Empty paths are skipped.
        directory (str | Path | None, optional): If given, also write each diagram to `<machine>_path_<NNN>.mmd` in this directory
            (created if needed). Defaults to None.
        direction (Literal["LR", "TB"], optional): Layout direction. Defaults to "LR".
        theme (str, optional): Mermaid theme. Defaults to "default".
        look (str, optional): Mermaid look. Defaults to "classic".
        layout (str, optional): Mermaid layout engine. Defaults to "dagre".
        show_actions (bool, optional): Whether to append each transition's actions to its edge label. Defaults to False.
        indent (int, optional): Spaces per indentation level. Defaults to 4.
        note_wrap_width (int | None, optional): Maximum characters per line in a description note. None disables wrapping. Defaults to 40.

    Returns:
        list[str]: One diagram per non-empty path, in the order given.

    """
    indent_str = " " * indent
    states_by_name = Machine.flatten(machine.states)
    state_types = {name: s.type for name, s in states_by_name.items()}
    non_empty = [p for p in paths if p]
    out_dir = Path(directory) if directory else None
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
    diagrams: list[str] = []
    for number, path in enumerate(non_empty, start=1):
        first, last = path[0].src, path[-1].tgt
        visited_before_last_edge = {first, *(t.tgt for t in path[:-1])}
        closes_cycle = last in visited_before_last_edge
        title = f"{machine.name} - path {number} of {len(non_empty)}" + (f" (loops back to {last})" if closes_cycle else "")
        lines = [
            "---",
            f"title: {title}",
            "config:",
            f"{indent_str}theme: {theme}",
            f"{indent_str}look: {look}",
            f"{indent_str}layout: {layout}",
            "---",
            "stateDiagram-v2",
            f"{indent_str}direction {direction}",
        ]
        for state in dict.fromkeys([first, *(t.tgt for t in path)]):
            match state_types.get(state):
                case StateType.DECISION | StateType.JUNCTION:
                    lines.append(f"{indent_str}state {state} <<choice>>")
                case StateType.JOIN:
                    lines.append(f"{indent_str}state {state} <<join>>")
                case StateType.FORK:
                    lines.append(f"{indent_str}state {state} <<fork>>")
        if state_types.get(first) in {StateType.INITIAL, StateType.ENTRY}:
            lines.append(f"{indent_str}[*] --> {first}")
        for step, t in enumerate(path, start=1):
            label = _transition_label(t, include_actions=show_actions)
            lines.append(f"{indent_str}{t.src} --> {t.tgt} : {step}. {label}".rstrip())
        if not closes_cycle and state_types.get(last) in {StateType.FINAL, StateType.TERMINAL, StateType.EXIT}:
            lines.append(f"{indent_str}{last} --> [*]")
        for state in dict.fromkeys([first, *(t.tgt for t in path)]):
            description = states_by_name[state].description if state in states_by_name else None
            if description:
                lines.append(f"{indent_str}note left of {state}")
                lines.extend(f"{indent_str * 2}{line}" for line in _wrap_description(description, note_wrap_width))
                lines.append(f"{indent_str}end note")
        diagram = "\n".join(lines)
        diagrams.append(diagram)
        if out_dir is not None:
            (out_dir / f"{machine.name}_path_{number:03d}.mmd").write_text(diagram, encoding="utf-8")
    return diagrams
