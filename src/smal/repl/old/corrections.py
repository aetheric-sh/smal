# """Module for the `smal rules` command group, which allows users to inspect and manage SMAL validation rules."""

# from __future__ import annotations  # Until Python 3.14

# import typer
# from rich.console import Console

# from smal.cli.commands.helpers import echo_table, get_persistence
# from smal.utilities.corrections import ALL_CORRECTIONS

# console = Console()

# corrections_app = typer.Typer(help="Inspect and manage SMAL corrections.")


# @corrections_app.callback(invoke_without_command=True)
# def corrections_root(ctx: typer.Context) -> None:
#     """Default command for the corrections app.

#     Args:
#         ctx (typer.Context): The Typer context object, used to determine if a subcommand was invoked.

#     """
#     if ctx.invoked_subcommand is None:
#         ctx.invoke(list_corrections_cmd)


# @corrections_app.command("list", help="List all corrections that SMAL can apply to state machines. Invoking `smal corrections` invokes this as well.")
# def list_corrections_cmd() -> None:
#     """Command to list all corrections and their enabled status to the user."""
#     persistence = get_persistence()
#     # Persistence should always have all corrections in its corrections dict
#     corrections = [next(c for c in ALL_CORRECTIONS if c.name == correction_name) for correction_name in persistence.corrections]
#     corrections_data = [(c.name, str(persistence.is_correction_enabled(c)), c.description) for c in corrections]
#     echo_table("SMAL Corrections", ["Name", "Enabled", "Description"], corrections_data)


# @corrections_app.command("disable", help="Disable 1 or more corrections from being applied.")
# def disable_correction_cmd(name: str = typer.Argument(..., help="The name of the correction to disable, or 'all' to disable all.")) -> None:
#     """Command to disable one correction or all corrections from being applied during validation."""
#     persistence = get_persistence()
#     if name.lower() == "all":
#         for c in ALL_CORRECTIONS:
#             persistence.enable_correction(c.name, False, write_to_file=False)
#         console.print("[green]All corrections have been disabled.[/green]")
#     else:
#         correction = next((c for c in ALL_CORRECTIONS if c.name == name), None)
#         if correction is None:
#             typer.BadParameter(f"Unknown correction '{name}'. Run the `smal corrections` command for list of valid corrections.")
#         else:
#             persistence.enable_correction(correction.name, False, write_to_file=False)
#             console.print(f"[green]Correction '{correction.name}' has been disabled.[/green]")
#     persistence.save()


# @corrections_app.command("enable", help="Enable 1 or more corrections to be applied.")
# def enable_correction_cmd(name: str = typer.Argument(..., help="The name of the correction to enable, or 'all' to enable all.")) -> None:
#     """Command to enable one correction or all corrections to be applied during validation."""
#     persistence = get_persistence()
#     if name.lower() == "all":
#         for c in ALL_CORRECTIONS:
#             persistence.enable_correction(c.name, True, write_to_file=False)
#         console.print("[green]All corrections have been enabled.[/green]")
#     else:
#         correction = next((c for c in ALL_CORRECTIONS if c.name == name), None)
#         if correction is None:
#             typer.BadParameter(f"Unknown correction '{name}'. Run the `smal corrections` command for list of valid corrections.")
#         else:
#             persistence.enable_correction(correction.name, True, write_to_file=False)
#             console.print(f"[green]Correction '{correction.name}' has been enabled.[/green]")
#     persistence.save()
