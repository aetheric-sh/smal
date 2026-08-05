# """Module for the `smal rules` command group, which allows users to inspect and manage SMAL validation rules."""

# from __future__ import annotations  # Until Python 3.14

# import typer
# from rich.console import Console

# from smal.cli.commands.helpers import echo_table, get_persistence
# from smal.utilities.rules import ALL_RULES

# console = Console()

# rules_app = typer.Typer(help="Inspect and manage SMAL validation rules.")


# @rules_app.callback(invoke_without_command=True)
# def rules_root(ctx: typer.Context) -> None:
#     """Default command for the rules app.

#     Args:
#         ctx (typer.Context): The Typer context object, used to determine if a subcommand was invoked.

#     """
#     if ctx.invoked_subcommand is None:
#         ctx.invoke(list_rules_cmd)


# @rules_app.command("list", help="List all rules that SMAL can evaulate against state machines. Invoking `smal rules` invokes this as well.")
# def list_rules_cmd() -> None:
#     """Command to list all rules and their enabled status to the user."""
#     persistence = get_persistence()
#     # Persistence should always have all rules in its rules dict
#     rules = [next(r for r in ALL_RULES if r.name == rule_name) for rule_name in persistence.rules]
#     rules_data = [(r.name, str(persistence.is_rule_enabled(r)), r.description) for r in rules]
#     echo_table("SMAL Ruleset", ["Name", "Enabled", "Description"], rules_data)


# @rules_app.command("disable", help="Disable 1 or more rules from being evaluated.")
# def disable_rule_cmd(name: str = typer.Argument(..., help="The name of the rule to disable, or 'all' to disable all.")) -> None:
#     """Command to disable one rule or all rules from being evaluated during validation."""
#     persistence = get_persistence()
#     if name.lower() == "all":
#         for r in ALL_RULES:
#             persistence.enable_rule(r.name, False, write_to_file=False)
#         console.print("[green]All rules have been disabled.[/green]")
#     else:
#         rule = next((r for r in ALL_RULES if r.name == name), None)
#         if rule is None:
#             typer.BadParameter(f"Unknown rule '{name}'. Run the `smal rules` command for list of valid rules.")
#         else:
#             persistence.enable_rule(rule.name, False, write_to_file=False)
#             console.print(f"[green]Rule '{rule.name}' has been disabled.[/green]")
#     persistence.save()


# @rules_app.command("enable", help="Enable 1 or more rules to be evaluated.")
# def enable_rule_cmd(name: str = typer.Argument(..., help="The name of the rule to enable, or 'all' to enable all.")) -> None:
#     """Command to enable one rule or all rules to be evaluated during validation."""
#     persistence = get_persistence()
#     if name.lower() == "all":
#         for r in ALL_RULES:
#             persistence.enable_rule(r.name, True, write_to_file=False)
#         console.print("[green]All rules have been enabled.[/green]")
#     else:
#         rule = next((r for r in ALL_RULES if r.name == name), None)
#         if rule is None:
#             typer.BadParameter(f"Unknown rule '{name}'. Run the `smal rules` command for list of valid rules.")
#         else:
#             persistence.enable_rule(rule.name, True, write_to_file=False)
#             console.print(f"[green]Rule '{rule.name}' has been enabled.[/green]")
#     persistence.save()
