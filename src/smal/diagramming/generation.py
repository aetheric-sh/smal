from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import Any

from graphviz import Digraph, ExecutableNotFound
from graphviz import FileExistsError as GraphvizFileExistsError

from smal.schemas import SMALFile, State, StateType, Transition


def all_descendant_states(state: State) -> set[str]:
    names = {state.name}
    for ss in state.substates:
        names |= all_descendant_states(ss)
    return names


def internal_edges(state: State, smal: SMALFile, added_edges: list[Transition]) -> list[Transition]:
    names = all_descendant_states(state)
    return [t for t in smal.get_all_transitions() if t.src_state in names and t.tgt_state in names and t.graphable and t not in added_edges]


def external_incoming_edges(state: State, smal: SMALFile, added_edges: list[Transition]) -> list[Transition]:
    names = all_descendant_states(state)
    return [t for t in smal.get_all_transitions() if t.tgt_state in names and t.src_state not in names and t.graphable and t not in added_edges]


def external_outgoing_edges(state: State, smal: SMALFile, added_edges: list[Transition]) -> list[Transition]:
    names = all_descendant_states(state)
    return [t for t in smal.get_all_transitions() if t.src_state in names and t.tgt_state not in names and t.graphable and t not in added_edges]


def create_edge_label(t: Transition) -> str:
    label = f"on: {t.evt}"
    if t.actions:
        label += f"\ndo: [{', '.join(t.actions)}]"
    if t.tgt_entry_evt:
        label += f"\non_entry: {t.tgt_entry_evt}"
    return label


def build_cluster_tree(smal: SMALFile, dot: Digraph, composite_state: State) -> Digraph:
    cluster_name = f"cluster_{composite_state.name}"
    cluster = Digraph(cluster_name)
    cluster.attr(
        label=composite_state.name,
        style="rounded,filled",
        color="#dddddd",
        fillcolor="#f8f8f8",
    )
    # Inject the ephemeral initial state for the cluster, which is required to exist
    ephemeral_initial_state = smal.get_ephemeral_state(composite_state.initial_substate)
    if ephemeral_initial_state is None:
        raise RuntimeError("Composite states must have an ephemeral initial substate.")
    cluster.node(ephemeral_initial_state.name, **StateType.INITIAL.default_metadata)
    # Add the real initial node
    graphed_type = ephemeral_initial_state.morphed_type or composite_state.type
    cluster.node(composite_state.initial_substate.name, **graphed_type.default_metadata)
    # Add the ephemeral transitions into and out of the ephemeral initial state
    added_edges = []
    incoming_eph_transitions = smal.get_incoming_ephemeral_transitions(ephemeral_initial_state)
    for iet in incoming_eph_transitions:
        dot.edge(iet.src_state, iet.tgt_state, create_edge_label(iet))
        added_edges.append(iet)
    outgoing_eph_transitions = smal.get_outgoing_ephemeral_transitions(ephemeral_initial_state)
    for oet in outgoing_eph_transitions:
        cluster.edge(oet.src_state, oet.tgt_state, create_edge_label(oet))
        added_edges.append(oet)
    # Add all non-initial root substates
    for rss in [ss for ss in composite_state.substates if not ss.substates and ss.type != StateType.INITIAL]:
        cluster.node(rss.name, **rss.type.default_metadata)
    # Internal edges
    for ie in internal_edges(composite_state, smal, added_edges=added_edges):
        cluster.edge(ie.src_state, ie.tgt_state, label=create_edge_label(ie))
    # External incoming edges
    for eie in external_incoming_edges(composite_state, smal, added_edges=added_edges):
        dot.edge(eie.src_state, eie.tgt_state, label=create_edge_label(eie), lhead=cluster_name)
    # External outgoing edges
    for eoe in external_outgoing_edges(composite_state, smal, added_edges=added_edges):
        dot.edge(eoe.src_state, eoe.tgt_state, label=create_edge_label(eoe), ltail=cluster_name)
    # Now recurse over nested substates
    for nss in [ss for ss in composite_state.substates if ss.substates]:
        subtree = build_cluster_tree(smal, cluster, nss)
        cluster.subgraph(subtree)
    return cluster


def generate_state_machine_svg(
    smal_path: str | Path,
    svg_output_dir: str | Path,
    graph_attr: dict[str, Any] | None = None,
    node_attr: dict[str, Any] | None = None,
    edge_attr: dict[str, Any] | None = None,
    open: bool = False,
    force: bool = False,
    title: bool = True,
) -> Path:
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
        # 2. Add ephemeral initial state if applicable (should only be 1 at root level)
        if rs.type == StateType.INITIAL:
            eph_init = smal.get_ephemeral_state(rs)
            dot.node(eph_init.name, **StateType.INITIAL.default_metadata)
            eph_transit = smal.get_outgoing_ephemeral_transitions(eph_init)
            if len(eph_transit) != 1:
                raise RuntimeError("Root-level initial states can only have 1 ephemeral incoming transition. This should never happen.")
            dot.edge(eph_init.name, rs.name)  # NOTE: Purposefully no label here
            graphed_type = eph_init.morphed_type or rs.type
            dot.node(rs.name, **graphed_type.default_metadata)
        else:
            dot.node(rs.name, **rs.type.default_metadata)
        # 3. Add all root-to-root edges (root-to-cluster/cluster-to-root will be added later)
        incoming_root_edges = [
            t for t in smal.transitions if t.src_state in root_state_names and t.src_state != rs.name and t.tgt_state == rs.name and t not in added_root_edges and t.graphable
        ]
        outgoing_root_edges = [
            t for t in smal.transitions if t.tgt_state in root_state_names and t.tgt_state != rs.name and t.src_state == rs.name and t not in added_root_edges and t.graphable
        ]
        for ire in incoming_root_edges:
            dot.edge(ire.src_state, ire.tgt_state, create_edge_label(ire))
            added_root_edges.append(ire)
        for ore in outgoing_root_edges:
            dot.edge(ore.src_state, ore.tgt_state, create_edge_label(ore))
            added_root_edges.append(ore)

    # 4. For each composite state
    composite_states = [s for s in smal.states if s.substates]
    for cs in composite_states:
        # Build the cluster tree, adding edges as we go
        cluster = build_cluster_tree(smal, dot, cs)
        # Add the cluster to the root graph
        dot.subgraph(cluster)

    # 5. Save output
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
