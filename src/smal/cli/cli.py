import typer

from smal.cli.commands import install_graphviz

app = typer.Typer()


@app.command()
def install_graphviz_cmd():
    """Install or guide installation of Graphviz."""
    install_graphviz()


if __name__ == "__main__":
    app()
