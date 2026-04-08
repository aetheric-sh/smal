"""Module defining the clean CLI command for removing SMAL application data."""

from __future__ import annotations  # Until Python 3.14

import typer
from rich.console import Console

from smal.utilities.persistence import SMALPersistence

clean_app = typer.Typer(help="Remove SMAL's persisted application data.")


@clean_app.callback(invoke_without_command=True)
def clean_root() -> None:
    """Remove SMAL's persisted application data directory."""
    console = Console()
    app_dir = SMALPersistence.DEFAULT_PATH.parent
    if not app_dir.exists():
        console.print("[yellow]Nothing to clean — no application data directory found.[/yellow]")
        raise typer.Exit
    SMALPersistence.clean()
    console.print(f"[green]Removed application data directory: {app_dir}[/green]")
