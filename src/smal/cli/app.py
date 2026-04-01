from __future__ import annotations  # Until Python 3.14

import typer

from smal.cli.commands import code_app, diagram_app, graphviz_app, rules_app, validate_app

app = typer.Typer(help="SMAL = State Machine Abstraction Language CLI")
app.add_typer(code_app, name="code")
app.add_typer(diagram_app, name="diagram")
app.add_typer(graphviz_app, name="graphviz")
app.add_typer(rules_app, name="rules")
app.add_typer(validate_app, name="validate")

if __name__ == "__main__":
    app()
