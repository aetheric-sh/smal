"""Module defining functions for generating Graphviz diagrams of SMAL state machines."""

from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import Any

from graphviz import Digraph, ExecutableNotFound
from graphviz import FileExistsError as GraphvizFileExistsError

from smal.schemas import SMALFile, State, StateType, Transition


def all_descendant_states(state: State) -> set[str]:
    """Get a flattened set of all descendent states of the given state (inclusive of the given state).

    Args:
        state (State): The state for which to find all descendant states.

    Returns:
        set[str]: A set of names of all descendant states, including the given state.

    """
    names = {state.name}
    for ss in state.substates:
        names |= all_descendant_states(ss)
    return names


def build_cluster_tree(smal: SMALFile, dot: Digraph, composite_state: State) -> Digraph:
    """Recursively build a tree of nodes to comprise a cluster.

    Args:
        smal (SMALFile): The SMAL file containing the state machine definition.
        dot (Digraph): The Graphviz Digraph object to which the cluster will be added.
        composite_state (State): The composite state for which the cluster is being built.

    Raises:
        RuntimeError: If the composite state does not have an ephemeral initial substate.

    Returns:
        Digraph: The Graphviz Digraph object representing the cluster.

    """
    cluster_name = f"cluster_{composite_state.name}"
    cluster = Digraph(cluster_name)
    cluster.attr(
        label=composite_state.name,
        style="rounded,filled",
        color="#dddddd",
        fillcolor="#f8f8f8",
    )
    # Add the initial node
    initial_substate = composite_state.initial_substate
    cluster.node(initial_substate.name, **initial_substate.type.default_metadata)
    # Add all non-initial root substates
    added_edges = []
    for rss in [ss for ss in composite_state.substates if not ss.substates and ss.type != StateType.INITIAL]:
        cluster.node(rss.name, **rss.type.default_metadata)
    # Internal edges
    for ie in internal_edges(composite_state, smal, added_edges=added_edges):
        cluster.edge(ie.src, ie.tgt, label=create_edge_label(ie))
    # External incoming edges
    for eie in external_incoming_edges(composite_state, smal, added_edges=added_edges):
        dot.edge(eie.src, eie.tgt, label=create_edge_label(eie), lhead=cluster_name)
    # External outgoing edges
    for eoe in external_outgoing_edges(composite_state, smal, added_edges=added_edges):
        dot.edge(eoe.src, eoe.tgt, label=create_edge_label(eoe), ltail=cluster_name)
    # Now recurse over nested substates
    for nss in [ss for ss in composite_state.substates if ss.substates]:
        subtree = build_cluster_tree(smal, cluster, nss)
        cluster.subgraph(subtree)
    return cluster


def create_edge_label(t: Transition) -> str:
    """Create an edge label for the given transition.

    Args:
        t (Transition): The transition for which to create the edge label.

    Returns:
        str: The edge label for the given transition.

    """
    label = f"on: {t.evt}"
    if t.actions:
        label += f"\ndo: [{', '.join(t.actions)}]"
    if t.tgt_entry_evt:
        label += f"\non_entry: {t.tgt_entry_evt}"
    return label


def external_incoming_edges(state: State, smal: SMALFile, added_edges: list[Transition]) -> list[Transition]:
    """Get the list of external incoming edges for the given state.

    Args:
        state (State): The state for which to find external incoming edges.
        smal (SMALFile): The SMAL file containing the state machine definition.
        added_edges (list[Transition]): The list of edges that have already been added.

    Returns:
        list[Transition]: The list of external incoming edges for the given state.

    """
    names = all_descendant_states(state)
    return [t for t in smal.transitions if t.tgt in names and t.src not in names and t not in added_edges]


def external_outgoing_edges(state: State, smal: SMALFile, added_edges: list[Transition]) -> list[Transition]:
    """Get the list of external outgoing edges for the given state.

    Args:
        state (State): The state for which to find external outgoing edges.
        smal (SMALFile): The SMAL file containing the state machine definition.
        added_edges (list[Transition]): The list of edges that have already been added.

    Returns:
        list[Transition]: The list of external outgoing edges for the given state.

    """
    names = all_descendant_states(state)
    return [t for t in smal.transitions if t.src in names and t.tgt not in names and t not in added_edges]


def generate_state_machine_svg(
    smal_path: str | Path,
    svg_output_dir: str | Path,
    graph_attr: dict[str, Any] | None = None,
    node_attr: dict[str, Any] | None = None,
    edge_attr: dict[str, Any] | None = None,
    open: bool = False,  # noqa: A002 - Shadows python builtin
    force: bool = False,
    title: bool = True,
) -> Path:
    """Generate an SVG graphviz diagram of the SMAL state machine from the file at the given path.

    Args:
        smal_path (str | Path): The path to the SMAL file to parse and generate a diagram for.
        svg_output_dir (str | Path): The directory to output the generated SVG file to.
        graph_attr (dict[str, Any] | None, optional): Attributes for the graph. Defaults to None.
        node_attr (dict[str, Any] | None, optional): Attributes for the nodes. Defaults to None.
        edge_attr (dict[str, Any] | None, optional): Attributes for the edges. Defaults to None.
        open (bool, optional): Whether to open the generated SVG file after creation. Defaults to False.
        force (bool, optional): Whether to overwrite existing files. Defaults to False.
        title (bool, optional): Whether to include a title in the diagram. Defaults to True.

    Raises:
        FileExistsError: If the output file already exists and force is False.
        ExecutableNotFound: If the Graphviz executable is not found.

    Returns:
        Path: The path to the generated SVG file.

    """
    # Parse the SMAL file
    smal = SMALFile.from_file(smal_path)
    # Set the properties and create the top-level graph
    default_graph_attr = {"rankdir": "LR", "fontname": "Arial", "splines": "polyline", "ranksep": "0.75", "nodesep": "0.75", "compound": "true"}
    default_graph_attr.update(graph_attr or {})
    default_node_attr = {"shape": "box", "style": "filled", "fillcolor": "#f8f8f8"}
    default_node_attr.update(node_attr or {})
    default_edge_attr = {"fontsize": "10", "color": "#555555"}
    default_edge_attr.update(edge_attr or {})
    dot = Digraph(
        name=smal.name,
        format="svg",
        graph_attr=default_graph_attr,
        node_attr=default_node_attr,
        edge_attr=default_edge_attr,
    )
    # Optionally, add a title
    if title:
        dot.attr(label=smal.name, labelloc="t", fontsize="20", fontname="Arial Bold")

    # 1. Add all root states
    root_states = [s for s in smal.states if not s.substates]
    root_state_names = {rs.name for rs in root_states}
    added_root_edges = []
    for rs in root_states:
        dot.node(rs.name, **rs.type.default_metadata)
        # 2. Add all root-to-root edges (root-to-cluster/cluster-to-root will be added later)
        incoming_root_edges = [t for t in smal.transitions if t.src in root_state_names and t.src != rs.name and t.tgt == rs.name and t not in added_root_edges]
        outgoing_root_edges = [t for t in smal.transitions if t.tgt in root_state_names and t.tgt != rs.name and t.src == rs.name and t not in added_root_edges]
        for ire in incoming_root_edges:
            dot.edge(ire.src, ire.tgt, create_edge_label(ire))
            added_root_edges.append(ire)
        for ore in outgoing_root_edges:
            dot.edge(ore.src, ore.tgt, create_edge_label(ore))
            added_root_edges.append(ore)

    # 3. For each composite state
    composite_states = [s for s in smal.states if s.substates]
    for cs in composite_states:
        # Build the cluster tree, adding edges as we go
        cluster = build_cluster_tree(smal, dot, cs)
        # Add the cluster to the root graph
        dot.subgraph(cluster)

    # 4. Save output
    try:
        out_path = dot.render(
            filename=f"{smal.name.lower()}_state_machine_diagram",
            directory=svg_output_dir,
            cleanup=True,
            raise_if_result_exists=not force,
        )
        out_path = Path(out_path)
    except GraphvizFileExistsError as e:
        raise FileExistsError(f"Output SVG file already exists: {out_path}. Use --force to overwrite.") from e
    except ExecutableNotFound as e:
        raise ExecutableNotFound("Graphviz not found. Install via: smal install-graphviz") from e

    if open:
        import webbrowser

        webbrowser.open(out_path.as_uri())

    return out_path


def internal_edges(state: State, smal: SMALFile, added_edges: list[Transition]) -> list[Transition]:
    """Get the list of internal edges for the given state.

    Args:
        state (State): The state for which to find internal edges.
        smal (SMALFile): The SMAL file containing the state machine definition.
        added_edges (list[Transition]): The list of edges that have already been added.

    Returns:
        list[Transition]: The list of internal edges for the given state.

    """
    names = all_descendant_states(state)
    return [t for t in smal.transitions if t.src in names and t.tgt in names and t not in added_edges]
