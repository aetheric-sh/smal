from pathlib import Path
from typing import Any

from graphviz import Digraph, ExecutableNotFound

from smal.schemas.smal_file import SMALFile


def generate_state_machine_svg(
    smal_path: str | Path,
    svg_output_dir: str | Path,
    graph_attr: dict[str, Any] | None = None,
    node_attr: dict[str, Any] | None = None,
    edge_attr: dict[str, Any] | None = None,
) -> None:
    smal_path = Path(smal_path)
    if not smal_path.is_file():
        raise ValueError(f"Invalid filepath for SMAL file: {smal_path}")
    svg_output_dir = Path(svg_output_dir)
    if not svg_output_dir.is_dir():
        raise ValueError(f"Invalid SVG output dir: {svg_output_dir}")

    # Parse the SMAL file
    smal = SMALFile.from_file(smal_path)

    default_graph_attr = {"rankdir": "LR", "fontname": "Arial", "splines": "polyline", "ranksep": "0.75", "nodesep": "0.75"}
    default_graph_attr.update(graph_attr or {})
    default_node_attr = {"shape": "box", "style": "filled", "fillcolor": "#f8f8f8"}
    default_node_attr.update(node_attr or {})
    default_edge_attr = {"fontsize": "10", "color": "#555555"}
    default_edge_attr.update(edge_attr or {})

    # Create a graphviz Digraph using the SMAL file
    dot = Digraph(
        name=smal.machine,
        format="svg",
        graph_attr=default_graph_attr,
        node_attr=default_node_attr,
        edge_attr=default_edge_attr,
    )

    # Add states
    for state in smal.states:
        dot.node(state.name, shape=state.type.graphviz_shape)

    # Add transitions
    for t in smal.transitions:
        label = f"on: {t.trigger_evt}\ndo: {t.action}{'entry: ' + t.landing_state_entry_evt if t.landing_state_entry_evt else ''}"
        dot.edge(t.trigger_state, t.landing_state, label=label)

    # Render the SVG file
    try:
        dot.render(filename=smal.machine.lower(), directory=svg_output_dir, cleanup=True)
    except ExecutableNotFound as e:
        raise ExecutableNotFound("Unable to find Graphviz executable on path. To install it, please run the 'smal install-graphviz' command.") from e
