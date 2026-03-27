from __future__ import annotations
from smal.codegen.code_generator import SMALCodeGenerator
from smal.schemas.smal_file import SMALFile
from pathlib import Path

if __name__ == "__main__":
    templates_dir = Path(__file__).parent / "codegen" / "c"
    examples_dir = Path(__file__).parent.parent / "examples"
    expanded_example = examples_dir / "example.smal"
    inlined_example = examples_dir / "example_inlined.smal"
    smal = SMALFile.from_file(expanded_example)
    codegen = SMALCodeGenerator(templates_dir)
    out_path = Path(__file__).parent / "example.h"
    codegen.render_to_file("state_machine_abstraction.h.j2", smal, out_path, header_guard="EXAMPLE_H")
    print("Done")
