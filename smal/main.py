from __future__ import annotations

from pathlib import Path

from smal.diagramming.generation import generate_state_machine_svg

if __name__ == "__main__":
    templates_dir = Path(__file__).parent / "codegen" / "c"
    examples_dir = Path(__file__).parent.parent / "examples"
    expanded_example = examples_dir / "example.smal"
    svg_out = examples_dir / "example_diagram.svg"
    # inlined_example = examples_dir / "example_inlined.smal"
    # smal = SMALFile.from_file(expanded_example)
    # codegen = SMALCodeGenerator(templates_dir)
    # out_path = Path(__file__).parent / "example.h"
    # codegen.render_to_file("state_machine_abstraction.h.j2", smal, out_path, header_guard="EXAMPLE_H")
    generate_state_machine_svg(expanded_example, svg_out)
    print("Done")
