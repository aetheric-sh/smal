from __future__ import annotations  # Until Python 3.14

import platform
import shutil
import subprocess

import typer
from rich.console import Console

from .helpers import echo_list

console = Console()

graphviz_app = typer.Typer(help="Install or guide installation of the Graphviz system package.", invoke_without_command=True)


@graphviz_app.callback()
def graphviz_root() -> None:
    console.print("🔍 [bold]Checking for Graphviz (`dot`)...[/bold]")
    dot_path = shutil.which("dot")
    if dot_path:
        console.print(f"✅ [green]Graphviz is already installed[/green] at: [cyan]{dot_path}[/cyan]")
        return
    console.print("❌ [red]Graphviz not found.[/red]")
    system = platform.system()
    match system:
        case "Windows":
            console.print("➡️  [bold]Windows detected[/bold].")
            console.print("Install Graphviz using the official installer:")
            console.print("[cyan]https://graphviz.org/download/[/cyan]")
            echo_list("Recommended", ["Download the 'Graphviz Windows Installer (EXE)'", "Run it and check 'Add Graphviz to the system PATH'"], tab_size=4)
        case "Darwin":
            console.print("➡️  [bold]macOS detected[/bold].")
            echo_list("Install Graphviz with Homebrew", ["[code]brew install graphviz[/code]"], tab_size=4, bold_header=False)
            echo_list("Or download from", ["https://graphviz.org/download/"], tab_size=4, bold_header=False)
            if shutil.which("brew"):
                console.print("🍺  [green]Homebrew detected[/green] — running install command...")
                subprocess.run(["brew", "install", "graphviz"])
        case "Linux":
            console.print("➡️  [bold]Linux detected[/bold].")
            echo_list(
                "Install Graphviz using your package manager",
                ["Debian/Ubuntu: [code]sudo apt install graphviz[/code]", "Fedora: [code]sudo dnf install graphviz[/code]", "Arch: [code]sudo pacman -S graphviz[/code]"],
                tab_size=4,
                bold_header=False,
            )
            echo_list("Or download from", ["https://graphviz.org/download/"], tab_size=4, bold_header=False)
        case _:
            console.print(f"⚠️  [yellow]Unsupported OS[/yellow]: {system}")
            echo_list("Please install Graphviz manually from", ["https://graphviz.org/download/"], tab_size=4, bold_header=False)
    echo_list("Once installed, verify your installation with", ["[code]dot -V[/code]"], tab_size=4, bold_header=False)
